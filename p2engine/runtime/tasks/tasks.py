from __future__ import annotations
import os
import time
from datetime import datetime, timedelta
from typing import Any, Dict, List, TYPE_CHECKING
import redis
from infra.artifacts.bus import get_bus
from infra.logging.effect_log import append_effect_log
from infra.logging.logging_config import logger
from infra.utils.session_helpers import current_episode_id
from orchestrator.interactions.states.tool_result import ToolResultState
from orchestrator.interactions.states.waiting import WaitingState
from runtime.post_effects import handle_post_effect
from runtime.task_runner import get_task_context
from runtime.task_runner.constants import MAX_ROUNDS
from runtime.tasks.celery_app import app

if TYPE_CHECKING:
    from runtime.effects import BaseEffect

TICK_FENCE_TTL: int = int(os.getenv("TICK_FENCE_TTL", 60))


def enqueue_session_tick(conversation_id: str, delay_sec: int = 0) -> None:
    eta = None
    if delay_sec > 0:
        eta = datetime.utcnow() + timedelta(seconds=delay_sec)
    app.send_task(
        "runtime.tasks.tasks.process_session_tick",
        args=[conversation_id],
        queue="ticks",
        eta=eta,
    )
    logger.debug(
        {
            "message": "enqueue_session_tick",
            "conversation_id": conversation_id,
            "delay_sec": delay_sec,
        }
    )


@app.task(name="runtime.tasks.tasks.process_session_tick", queue="ticks")
def process_session_tick(conversation_id: str, round: int = 0) -> None:
    from infra.session import get_session

    ctx = get_task_context()
    r: redis.Redis = ctx["redis_client"]
    lock_key = f"tick_fence:{conversation_id}"
    if not r.set(lock_key, "1", ex=TICK_FENCE_TTL, nx=True):
        logger.info("Tick already in progress for %s – skipping", conversation_id)
        return
    try:
        get_session(conversation_id, r)
        agents_b = r.smembers(f"session:{conversation_id}:agents")
        if not agents_b:
            logger.error(
                {
                    "message": "tick_aborted_no_live_agents",
                    "conversation_id": conversation_id,
                }
            )
            return
        agents = [a.decode() if isinstance(a, bytes) else a for a in agents_b]
        from runtime.task_runner.agent_runner import process_agent_tick

        has_work = any(process_agent_tick(conversation_id, aid) for aid in agents)
        if has_work and round < MAX_ROUNDS:
            enqueue_session_tick(conversation_id)
        elif has_work:
            logger.warning("MAX_ROUNDS reached for conversation %s", conversation_id)
        logger.info("Session tick processed – conversation_id=%s", conversation_id)
    finally:
        r.delete(lock_key)


@app.task(name="runtime.tasks.tasks.execute_tool", queue="tools")
def execute_tool(
    conversation_id: str,
    agent_id: str,
    tool_name: str,
    parameters: Dict[str, Any],
    tool_call_id: str,
    branch_id: str,
    tool_state_env: Dict[str, Any],
) -> None:
    from infra.session import get_session
    from runtime.effects import BaseEffect

    ctx = get_task_context()
    r: redis.Redis = ctx["redis_client"]
    session = get_session(conversation_id, r)
    stack = session.stack_for(agent_id)
    tool = ctx["tool_registry"].get_tool_by_name(tool_name)
    try:
        if tool is None:
            raise RuntimeError(f"Tool '{tool_name}' not found")
        t0 = time.time()
        exec_kwargs: Dict[str, Any] = {
            "redis_client": r,
            "conversation_id": conversation_id,
            "creator_id": agent_id,
            "branch_id": branch_id,
            **parameters,
        }
        data = tool.execute(**exec_kwargs)
        latency_ms = int((time.time() - t0) * 1000)
        cache_status = data.pop("cache_status", "unknown")
        reward: float = 1.0
        result = {"status": "ok", "result": data}
        meta = {"status": "executed", "cache": cache_status, "latency_ms": latency_ms}
    except Exception as exc:
        logger.error(
            {
                "message": "tool_execution_failed",
                "tool": tool_name,
                "conversation_id": conversation_id,
                "error": str(exc),
            },
            exc_info=True,
        )
        latency_ms = 0
        reward = 0.0
        result = {"status": "error", "message": str(exc)}
        meta = {"status": "error", "error": str(exc)}
    from infra.logging.interaction_log import log_interaction_event

    log_interaction_event(
        conversation_id=conversation_id,
        event_type="tool_result",
        agent_id=agent_id,
        correlation_id=tool_call_id,
        payload={"tool_name": tool_name, "result": result},
    )
    entry = stack.current()
    if not (isinstance(entry.state, WaitingState) and entry.state.correlation_id == tool_call_id):
        raise RuntimeError("Stack corruption: expected WaitingState for tool_call_id")
    stack.pop()
    stack.push(
        ToolResultState(
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            result=result,
            arguments=parameters,
            reward=reward,
        )
    )
    extra_effects: List["BaseEffect"] = []
    for pe_name in tool.config.post_effects or []:
        extra_effects.extend(
            handle_post_effect(
                pe_name,
                conversation_id=conversation_id,
                agent_id=agent_id,
                stack=stack,
                parameters=parameters,
                result=result,
                redis_client=r,
            )
        )
    for eff in extra_effects:
        try:
            eff.execute(r)
        except Exception as exc:
            logger.error(
                {
                    "message": "post_effect_failed",
                    "effect": type(eff).__name__,
                    "conversation_id": conversation_id,
                    "error": str(exc),
                },
                exc_info=True,
            )
    try:
        bus = get_bus()
        episode_id = current_episode_id(r, conversation_id, agent_id, branch_id)
        model_field = f"tools/{tool_name}@{tool.__module__}" if tool else f"tools/{tool_name}"
        header = {
            "session_id": conversation_id,
            "agent_id": agent_id,
            "branch_id": branch_id,
            "episode_id": episode_id,
            "role": "metrics",
            "mime": "application/json",
            "model": model_field,
            "latency_ms": latency_ms,
            "prompt_tokens": None,
            "completion_tokens": None,
            "reward": reward,
        }
        team_id_val = r.get(f"{conversation_id}:team")
        variant_id_val = r.get(f"{conversation_id}:variant")
        if team_id_val or variant_id_val:
            header["meta"] = header.get("meta", {})
            if team_id_val:
                header["meta"]["team_id"] = team_id_val if isinstance(team_id_val, str) else team_id_val.decode()
            if variant_id_val:
                header["meta"]["variant_id"] = variant_id_val if isinstance(variant_id_val, str) else variant_id_val.decode()
        if result["status"] == "ok" and isinstance(result["result"], dict):
            cost = result["result"].get("cost_usd")
            if cost is not None:
                header["cost_usd"] = cost
        bus.publish(header, {"status": result["status"], "cache": meta.get("cache")})
    except Exception as exc:
        logger.error(
            {
                "message": "tool_metrics_publish_failed",
                "tool": tool_name,
                "conversation_id": conversation_id,
                "error": str(exc),
            },
            exc_info=True,
        )
    r.delete(f"round_by_branch:{conversation_id}:{agent_id}:{branch_id}")
    append_effect_log(
        conversation_id,
        {
            "branch_id": branch_id,
            "tool_name": tool_name,
            "parameters": parameters,
            "meta": meta,
        },
    )
    enqueue_session_tick(conversation_id)
    logger.info(
        {
            "message": "tool_executed",
            "tool_name": tool_name,
            "conversation_id": conversation_id,
        }
    )
