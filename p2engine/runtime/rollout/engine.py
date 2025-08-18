import os
import hashlib
import json
import time
import asyncio
from typing import Optional, Dict, Any, List

from celery import chain, chunks, group

from agents.persona_registry import get_required_tools
from runtime.tasks.rollout_tasks import (
    finalise_rollout,
    run_variant,
    trigger_eval,
    wait_for_eval,
    wait_for_session,
)
from services.services import ServiceContainer
from .expander import expand_variants
from .spec import MultiRolloutSpec
from .store import RolloutStore
from infra.async_utils import run_async
from infra.logging.logging_config import logger

_container = ServiceContainer()
_rds = _container.get_redis_client()


async def capture_ledger_snapshot(label: str, agent_ids: List[str], wait_for_settle: bool = False) -> Dict[str, Any]:
    if os.getenv("LEDGER_ENABLED", "true") != "true":
        return {"label": label, "enabled": False}
    if wait_for_settle:
        logger.info(f"Waiting for ledger transactions to settle before {label} snapshot...")
        await asyncio.sleep(5)
    try:
        from services.ledger_service import get_ledger_service

        ledger = await get_ledger_service()

        # Clear the wallet cache to ensure fresh data
        ledger._wallet_cache.clear()

        metrics = await ledger.get_system_metrics()
        wallets = []
        for agent_id in agent_ids:
            try:
                # Force fresh balance read with use_cache=False
                balance = await ledger.get_agent_balance(agent_id, use_cache=False)
                history = await ledger.get_transaction_history(agent_id, limit=10000)
                wallets.append(
                    {
                        "agent_id": agent_id,
                        "balance": balance,
                        "transaction_count": len(history),
                        "transactions": history,
                    }
                )
            except Exception as e:
                logger.debug(f"Could not get balance for {agent_id}: {e}")
                wallets.append({"agent_id": agent_id, "balance": 0.0, "transaction_count": 0, "error": str(e)})
        return {"label": label, "timestamp": time.time(), "enabled": True, "metrics": metrics, "wallets": wallets}
    except Exception as exc:
        logger.warning(f"Failed to capture ledger snapshot: {exc}")
        return {"label": label, "enabled": False, "error": str(exc)}


def run_rollout(
    multi_spec: MultiRolloutSpec,
    parallel_hint: Optional[int] = None,
    strict_tools: bool = False,
) -> str:
    total_variants = 0
    all_agent_ids = set()
    for team_id, team_spec in multi_spec.teams.items():
        variants = expand_variants(team_spec)
        for idx, variant in enumerate(variants):
            if agent_id := variant.get("agent_id"):
                all_agent_ids.add(agent_id)
            if strict_tools:
                behavior_template = variant.get("behavior_template")
                if behavior_template:
                    required_tools = get_required_tools(behavior_template)
                    provided_tools = set(variant.get("tools", []))
                    missing = required_tools - provided_tools
                    if missing:
                        raise ValueError(
                            f"Team {team_id}, variant {idx}: missing tools " f"{sorted(missing)} for persona {behavior_template}"
                        )
        total_variants += len(variants)
    all_agent_ids.update(["treasurer", "agent_helper", "child"])
    rollout_id = f"multi:{time.time_ns()}"
    RolloutStore(_rds).create(rollout_id, total_variants)
    
    # NEW: Initialize Rerun logging for this rollout
# NEW: Initialize Rerun logging for this rollout
    from infra.observability.rerun_rollout import log_rollout_start, log_ledger_snapshot
    log_rollout_start(
        rollout_id=rollout_id,
        teams=len(multi_spec.teams),
        total_variants=total_variants,
        config={
            "teams": list(multi_spec.teams.keys()),
            "parallel_hint": parallel_hint,
            "strict_tools": strict_tools,
            "start_time": time.time()
        }
    )
    
    if os.getenv("LEDGER_ENABLED", "true") == "true":
        before_snapshot = run_async(capture_ledger_snapshot("before_rollout", list(all_agent_ids)))
        _rds.set(f"rollout:{rollout_id}:snapshot:before", json.dumps(before_snapshot), ex=86400)
        
        # NEW: Log to Rerun
        log_ledger_snapshot(rollout_id, "before", before_snapshot)
        
        logger.info(f"Captured before snapshot for rollout {rollout_id}")
    
    sigs = []
    for team_id, team_spec in multi_spec.teams.items():
        variants = expand_variants(team_spec)
        for idx, overrides in enumerate(variants):
            variant_id = f"{team_id}:v{idx:03d}"
            blob = json.dumps(overrides, sort_keys=True, separators=(",", ":")).encode()
            variant_hash = hashlib.sha1(blob).hexdigest()
            init_msg = overrides.get("initial_message") or team_spec.initial_message
            if not init_msg:
                raise ValueError(f"Neither team- nor variant-level initial_message supplied " f"for {team_id}/{variant_id}")
            seed = run_variant.s(
                team_id,
                variant_id,
                overrides,
                init_msg,
                None if team_spec.eval is None else team_spec.eval.model_dump(),
                rollout_id,
                variant_hash,
            )
            chain_steps = [seed, wait_for_session.s()]
            if team_spec.eval:
                chain_steps.extend([trigger_eval.s(), wait_for_eval.s()])
            chain_steps.append(finalise_rollout.s())
            sigs.append(chain(*chain_steps))
    if parallel_hint and parallel_hint > 0:
        chunks(sigs, parallel_hint).apply_async()
    else:
        group(sigs).apply_async()
    _rds.set(f"rollout:{rollout_id}:agents", json.dumps(list(all_agent_ids)), ex=86400)
    return rollout_id