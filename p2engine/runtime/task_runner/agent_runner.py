from __future__ import annotations
from typing import Any, Dict

from infra.artifacts.bus import get_bus
from infra.clock import ack_tick
from infra.logging.logging_config import logger
from infra.session import get_session
from infra.side_effect_executor import EffectExecutor
from infra.utils.session_helpers import current_episode_id
from orchestrator.interactions.states.finished import FinishedState
from runtime.agent_runtime import AgentRuntime
from runtime.task_runner.constants import MAX_ROUNDS
from runtime.tasks.celery_app import app as celery_app

ROUND_TTL: int = 86_400


def _ctx() -> Dict[str, Any]:
    from . import get_task_context

    return get_task_context()


def _is_finished(entry) -> bool:
    return bool(entry and isinstance(entry.state, FinishedState))


def _publish_finished(conversation_id: str, agent_id: str, branch_id: str) -> None:
    header = {
        "session_id": conversation_id,
        "agent_id": agent_id,
        "branch_id": branch_id,
        "role": "event",
        "type": "event",
        "mime": "application/json",
        "meta": {"event": "agent_finished"},
    }
    try:
        get_bus().publish(header, {})
    except Exception as exc:
        logger.error(
            {
                "message": "failed_to_publish_agent_finished",
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "error": str(exc),
            },
            exc_info=True,
        )


def process_agent_tick(conversation_id: str, agent_id: str) -> bool:
    ctx = _ctx()
    redis_client = ctx["redis_client"]
    dedup_policy = ctx["dedup_policy"]

    session = get_session(conversation_id, redis_client)
    stack = session.stack_for(agent_id)

    top_entry = stack.current()
    finished_on_entry = _is_finished(top_entry)

    agent = ctx["agent_registry"].get_agent(agent_id)
    if agent is None:
        logger.error({"message": "Agent not found", "agent_id": agent_id})
        return False

    branch_id = stack.current_branch()
    _ = current_episode_id(redis_client, conversation_id, agent_id, branch_id)

    rounds_key = f"round_by_branch:{conversation_id}:{agent_id}:{branch_id}"
    before_len = stack.length()

    runtime = AgentRuntime(agent, conversation_id, agent_id, stack)
    _, effects = runtime.step()
    after_len = stack.length()

    progressed = bool(effects)
    if not progressed and after_len > before_len:
        top = stack.current()
        progressed = isinstance(top.state, FinishedState)

    if progressed:
        redis_client.delete(rounds_key)
        rounds = 0
    else:
        rounds = redis_client.incr(rounds_key)
        redis_client.expire(rounds_key, ROUND_TTL)

    parent_agent_id = stack.get_parent_agent_id()
    current_frame = stack.current()

    if _is_finished(current_frame) and finished_on_entry and parent_agent_id is None:
        _publish_finished(conversation_id, agent_id, branch_id)
        redis_client.sadd(f"session:{conversation_id}:finished", agent_id)
        ack_tick(redis_client, conversation_id, agent_id, session.tick)
        session.unregister_agent(agent_id, force=True)
        return False

    if finished_on_entry and not effects and parent_agent_id is None:
        _publish_finished(conversation_id, agent_id, branch_id)
        redis_client.sadd(f"session:{conversation_id}:finished", agent_id)
        ack_tick(redis_client, conversation_id, agent_id, session.tick)
        session.unregister_agent(agent_id, force=True)
        return False

    if rounds > MAX_ROUNDS:
        logger.warning(
            {
                "message": "Max idle rounds reached – branch throttled",
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "branch_id": branch_id,
                "rounds": rounds,
            }
        )
        _publish_finished(conversation_id, agent_id, branch_id)
        redis_client.sadd(f"session:{conversation_id}:finished", agent_id)  
        ack_tick(redis_client, conversation_id, agent_id, session.tick)
        return False


    executor = EffectExecutor(redis_client, celery_app, dedup_policy)
    executor.execute(effects, conversation_id)

    current_tick = session.refresh_tick()
    ack_tick(redis_client, conversation_id, agent_id, current_tick)

    if _is_finished(stack.current()) and parent_agent_id is None:
        _publish_finished(conversation_id, agent_id, branch_id)
        redis_client.sadd(f"session:{conversation_id}:finished", agent_id)  
        session.unregister_agent(agent_id, force=True)

    logger.info(
        {
            "message": "Agent tick processed",
            "agent_id": agent_id,
            "conversation_id": conversation_id,
            "effects": len(effects),
        }
    )

    return progressed
