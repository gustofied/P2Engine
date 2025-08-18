from __future__ import annotations
import json
import os
import time
from typing import Any, Dict, List, Optional

from infra.async_utils import run_async
import redis
from celery import shared_task

from infra.artifacts.bus import get_bus
from infra.artifacts.schema import parse_timestamp
from infra.logging.logging_config import logger
from infra.session import get_session
from infra.utils.redis_helpers import serialise_for_redis
from orchestrator.interactions.render import render_for_llm
from orchestrator.interactions.states.user_message import UserMessageState
from runtime.rollout.spec import EvalSpec
from runtime.rollout.store import RolloutStore
from runtime.task_runner import get_task_context
from runtime.tasks.celery_app import app
from runtime.tasks.tasks import enqueue_session_tick


def _meta_status(fields: Dict[str, str]) -> Optional[str]:
    raw = fields.get("meta")
    if raw is None:
        return None
    if isinstance(raw, bytes):
        raw = raw.decode()
    try:
        meta = json.loads(raw) if isinstance(raw, str) else raw
    except (TypeError, json.JSONDecodeError):
        return None
    return meta.get("status") if isinstance(meta, dict) else None


@shared_task(name="runtime.tasks.rollout_tasks.wait_for_session", queue="ticks")
def wait_for_session(run_info: Dict[str, Any], timeout_sec: int = 900) -> Dict[str, Any]:
    conversation_id = run_info["conversation_id"]
    ctx = get_task_context()
    r: redis.Redis = ctx["redis_client"]

    deadline = time.time() + timeout_sec
    finished_key = f"session:{conversation_id}:finished"

    while time.time() < deadline:
        if r.scard(finished_key):
            return run_info
        time.sleep(2)

    raise RuntimeError(f"wait_for_session: conversation {conversation_id!r} did not " f"finish within {timeout_sec}s")


@app.task(name="runtime.tasks.rollout_tasks.run_variant", queue="rollouts")
def run_variant(
    team_id: str,
    variant_id: str,
    overrides: Dict[str, Any],
    initial_message: str,
    eval_cfg: Optional[Dict[str, Any]] = None,
    rollout_id: Optional[str] = None,
    variant_hash: Optional[str] = None,
) -> Dict[str, Any]:
    ctx = get_task_context()
    r: redis.Redis = ctx["redis_client"]

    agent_id: str | None = overrides.get("agent_id")
    if not agent_id:
        raise ValueError("Each variant needs an 'agent_id' field")

    conversation_id = f"rollout:{team_id}:{variant_id}:{time.time_ns()}"

    r.mset(
        {
            f"conversation:{conversation_id}:mode": "rollout",
            f"conversation:{conversation_id}:agent_id": agent_id,
            f"conversation:{conversation_id}:id": conversation_id,
            f"{conversation_id}:team": team_id,
            f"{conversation_id}:variant": variant_id,
            f"{conversation_id}:rollout_id": rollout_id or "",
        }
    )

    r.set(
        f"agent:{agent_id}:{conversation_id}:override",
        json.dumps(overrides),
        ex=86_400,
    )

    session = get_session(conversation_id, r)
    session.register_agent(agent_id)
    session.stack_for(agent_id).push(UserMessageState(text=initial_message))

    enqueue_session_tick(conversation_id)

    logger.info(
        {
            "message": "rollout_variant_launched",
            "conversation_id": conversation_id,
            "team_id": team_id,
            "variant_id": variant_id,
            "variant_hash": variant_hash,
            "rollout_id": rollout_id,
        }
    )

    return {
        "conversation_id": conversation_id,
        "team_id": team_id,
        "variant_id": variant_id,
        "agent_id": agent_id,
        "eval_cfg": eval_cfg,
        "rollout_id": rollout_id,
        "variant_hash": variant_hash,
        "overrides": overrides,
    }


@app.task(name="runtime.tasks.rollout_tasks.trigger_eval", queue="ticks")
def trigger_eval(run_info: Dict[str, Any]) -> Dict[str, Any]:
    eval_cfg = run_info.get("eval_cfg")
    if not eval_cfg:
        return run_info

    eval_spec = EvalSpec.model_validate(eval_cfg)
    if not eval_spec.prompts and not eval_spec.rubric:
        logger.info(
            "Skipping evaluation for %s/%s – empty prompt list & no rubric",
            run_info["team_id"],
            run_info["variant_id"],
        )
        return run_info

    ctx = get_task_context()
    r: redis.Redis = ctx["redis_client"]
    bus = get_bus()

    conversation_id = run_info["conversation_id"]
    agent_id = run_info["agent_id"]

    last_ref_key = f"stack:{conversation_id}:{agent_id}:last_assistant_ref"
    assistant_ref = r.get(last_ref_key)
    if not assistant_ref:
        logger.warning(
            {
                "message": "assistant_ref_missing",
                "conversation_id": conversation_id,
                "agent_id": agent_id,
            }
        )
        return run_info

    stack = get_session(conversation_id, r).stack_for(agent_id)
    traj_for_llm = render_for_llm(stack)

    from infra.evals.registry import registry

    judge = registry.get(eval_spec.evaluator_id)

    eval_ref = bus.create_evaluation_for(
        assistant_ref,
        evaluator_id=judge.id,
        judge_version=eval_spec.judge_version or judge.version,
        payload={
            "traj": traj_for_llm,
            "rubric": eval_spec.rubric,
            "parent_agent_id": None,
            "correlation_id": None,
            "child_agent_id": agent_id,
        },
    )

    run_info.update({"eval_ref": eval_ref, "eval_spec": eval_spec.model_dump()})
    return run_info


@app.task(name="runtime.tasks.rollout_tasks.wait_for_eval", queue="ticks")
def wait_for_eval(run_info: Dict[str, Any]) -> Dict[str, Any]:
    eval_ref = run_info.get("eval_ref")
    eval_spec_dict = run_info.get("eval_spec")

    if not eval_ref or not eval_spec_dict:
        return run_info

    eval_spec = EvalSpec.model_validate(eval_spec_dict)
    bus = get_bus()

    deadline = time.time() + eval_spec.timeout_sec
    stream = "stream:artifacts"
    last_id = "0-0"

    while True:
        if time.time() > deadline:
            logger.error(
                {
                    "message": "evaluation_timeout",
                    "evaluation_ref": eval_ref,
                    "conversation_id": run_info["conversation_id"],
                }
            )
            run_info["score"] = 0.0
            return run_info

        res = bus.redis.xread({stream: last_id}, block=1000, count=10)
        if not res:
            continue

        for _stream, msgs in res:
            for sid, raw in msgs:
                last_id = sid
                fields = {k.decode() if isinstance(k, bytes) else k: v.decode() if isinstance(v, bytes) else v for k, v in raw.items()}

                if fields.get("ref") == eval_ref and _meta_status(fields) == "finished":
                    hdr, _ = bus.get(eval_ref)
                    metric = eval_spec.metric

                    run_info["score"] = (
                        float(hdr.get("score"))
                        if metric == "score"
                        else float(hdr.get("meta", {}).get("eval_metrics", {}).get(metric, 0.0))
                    )
                    return run_info


@shared_task(name="runtime.tasks.rollout_tasks.finalise_rollout", queue="ticks")
def finalise_rollout(run_info: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize rollout with Rerun visualization logging."""
    conversation_id, team_id, variant_id, agent_id = (run_info[k] for k in ("conversation_id", "team_id", "variant_id", "agent_id"))
    rollout_id: Optional[str] = run_info.get("rollout_id")
    score = float(run_info.get("score", 0.0))
    variant_hash = run_info.get("variant_hash")
    overrides = run_info.get("overrides", {})

    ctx = get_task_context()
    r: redis.Redis = ctx["redis_client"]
    bus = get_bus()

    metrics: List[Dict[str, Any]] = [
        hdr for hdr, _ in bus.read_last_n(1000, session_id=conversation_id, role="metrics") if hdr.get("agent_id") == agent_id
    ]

    tokens = sum((m.get("prompt_tokens") or 0) + (m.get("completion_tokens") or 0) for m in metrics)
    cost_usd = sum(m.get("cost_usd") or 0.0 for m in metrics)

    first_hdr, _ = bus.read_first_n(1, session_id=conversation_id)[0]
    last_hdr, _ = bus.read_last_n(1, session_id=conversation_id)[0]
    wall = parse_timestamp(last_hdr["ts"]) - parse_timestamp(first_hdr["ts"])

    summary_raw = {
        "team_id": team_id,
        "variant_id": variant_id,
        "conversation_id": conversation_id,
        "rollout_id": rollout_id,
        "variant_hash": variant_hash,
        "score": score,
        "tokens": tokens,
        "wall_time": wall,
        "cost": cost_usd,
        "overrides": overrides,
    }

    # Ledger metrics collection (existing code)
    if os.getenv("LEDGER_ENABLED", "true") == "true":
        try:
            async def _get_ledger_metrics():
                from services.ledger_service import get_ledger_service

                ledger = await get_ledger_service()
                balance = await ledger.get_agent_balance(agent_id)
                all_history = await ledger.get_transaction_history(agent_id, limit=10000)

                net_flow = 0.0
                rollout_tx_count = 0
                rollout_start_time = parse_timestamp(first_hdr["ts"])

                for tx in all_history:
                    payload = tx.get("payload", {})
                    tx_timestamp = float(payload.get("timestamp", 0))

                    if tx_timestamp >= rollout_start_time:
                        rollout_tx_count += 1
                        amount = float(payload.get("amount", 0))

                        if payload.get("toAgent") == agent_id:
                            net_flow += amount  
                        elif payload.get("fromAgent") == agent_id:
                            net_flow -= amount  

                return {
                    "final_balance": balance,
                    "transaction_count": rollout_tx_count,
                    "net_flow": net_flow,
                }

            ledger_metrics = run_async(_get_ledger_metrics())
            summary_raw.update(ledger_metrics)

        except Exception as exc:
            logger.warning(f"Failed to collect ledger metrics: {exc}")

    # NEW: Log to Rerun
    from infra.observability.rerun_rollout import (
        log_variant_metrics, log_pareto_point, log_variant_config
    )
    
    # Log variant metrics
    log_variant_metrics(
        rollout_id=rollout_id or "unknown",
        team_id=team_id,
        variant_id=variant_id,
        score=score,
        tokens=tokens,
        cost=cost_usd,
        wall_time=wall,
        net_flow=summary_raw.get("net_flow", 0.0),
        final_balance=summary_raw.get("final_balance", 0.0),
        transaction_count=summary_raw.get("transaction_count", 0)
    )
    
    # Log for Pareto visualization
    log_pareto_point(
        rollout_id=rollout_id or "unknown",
        team_id=team_id,
        variant_id=variant_id,
        score=score,
        cost=cost_usd,
        tokens=tokens
    )
    
    # Log variant configuration
    log_variant_config(
        rollout_id=rollout_id or "unknown",
        team_id=team_id,
        variant_id=variant_id,
        config=overrides
    )

    # Write to Redis stream (existing code)
    try:
        bus.redis.xadd(
            "stream:rollout_results",
            serialise_for_redis(summary_raw),
            maxlen=10_000,
            approximate=True,
        )
    except Exception:
        logger.exception("Failed to write roll-out summary row")

    if rollout_id:
        store = RolloutStore(r)
        completed = store.incr_completed(rollout_id)
        _, total = store.progress(rollout_id)
        if completed >= total:
            store.mark_done(rollout_id)
            
            # NEW: Log final ledger snapshot when rollout is done
            if os.getenv("LEDGER_ENABLED", "true") == "true" and completed >= total:
                agent_ids_json = r.get(f"rollout:{rollout_id}:agents")
                if agent_ids_json:
                    agent_ids = json.loads(agent_ids_json)
                    after_snapshot = run_async(capture_ledger_snapshot("after_rollout", agent_ids, wait_for_settle=True))
                    r.set(f"rollout:{rollout_id}:snapshot:after", json.dumps(after_snapshot), ex=86400)
                    
                    from infra.observability.rerun_rollout import log_ledger_snapshot
                    log_ledger_snapshot(rollout_id, "after", after_snapshot)

    logger.info({"message": "rollout_variant_done", **summary_raw})
    return summary_raw


async def capture_ledger_snapshot(label: str, agent_ids: List[str], wait_for_settle: bool = False) -> Dict[str, Any]:
    """Helper function to capture ledger state."""
    if os.getenv("LEDGER_ENABLED", "true") != "true":
        return {"label": label, "enabled": False}
    if wait_for_settle:
        logger.info(f"Waiting for ledger transactions to settle before {label} snapshot...")
        await asyncio.sleep(5)
    try:
        from services.ledger_service import get_ledger_service

        ledger = await get_ledger_service()
        ledger._wallet_cache.clear()

        metrics = await ledger.get_system_metrics()
        wallets = []
        for agent_id in agent_ids:
            try:
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