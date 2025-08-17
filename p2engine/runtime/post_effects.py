from __future__ import annotations
from typing import Any, Callable, Dict, List, TYPE_CHECKING
import redis
from infra.logging.logging_config import logger
from orchestrator.interactions.states.agent_call import AgentCallState
from runtime.effects import BaseEffect, CallTool

if TYPE_CHECKING:
    from orchestrator.interactions.stack import InteractionStack

_POST_EFFECT_HANDLERS: Dict[str, Callable[..., List[BaseEffect]]] = {}


def register_post_effect(name: str) -> Callable[[Callable[..., List[BaseEffect]]], Callable[..., List[BaseEffect]]]:
    """Register a post-effect handler"""
    key = name.lower()

    def decorator(fn: Callable[..., List[BaseEffect]]):
        _POST_EFFECT_HANDLERS[key] = fn
        return fn

    return decorator


def handle_post_effect(
    name: str,
    *,
    conversation_id: str,
    agent_id: str,
    stack: "InteractionStack",
    parameters: Dict[str, Any],
    result: Dict[str, Any],
    redis_client: redis.Redis,
) -> List[BaseEffect]:
    """Handle a post-effect by name"""
    handler = _POST_EFFECT_HANDLERS.get(name.lower())
    if handler is None:
        logger.warning(
            "Unknown post-effect %r (tool=%s, conversation=%s)",
            name,
            parameters.get("tool_name"),
            conversation_id,
        )
        return []

    try:
        return handler(
            conversation_id=conversation_id,
            agent_id=agent_id,
            stack=stack,
            parameters=parameters,
            result=result,
            redis_client=redis_client,
        )
    except Exception as exc:
        logger.error(
            {
                "message": "Post-effect handler failed",
                "post_effect": name,
                "conversation_id": conversation_id,
                "agent_id": agent_id,
                "error": str(exc),
            },
            exc_info=True,
        )
        return []


@register_post_effect("agent_call")
def _agent_call_handler(
    *,
    conversation_id: str,
    agent_id: str,
    stack: "InteractionStack",
    parameters: Dict[str, Any],
    result: Dict[str, Any],
    redis_client: redis.Redis,
) -> List[BaseEffect]:
    """Handle agent delegation"""
    child_id = parameters.get("agent_id") or result.get("child")
    if not child_id:
        logger.error("agent_call post-effect missing child agent_id")
        return []

    message = parameters.get("message", "")
    stack.push(AgentCallState(agent_id=child_id, message=message))

    logger.info(
        {
            "event": "agent_call queued",
            "conversation_id": conversation_id,
            "parent_agent": agent_id,
            "child_agent": child_id,
        }
    )

    from runtime.tasks.tasks import enqueue_session_tick

    enqueue_session_tick(conversation_id)

    return []


@register_post_effect("treasurer_payment")
def _treasurer_payment_handler(
    *,
    conversation_id: str,
    agent_id: str,
    stack: "InteractionStack",
    parameters: Dict[str, Any],
    result: Dict[str, Any],
    redis_client: redis.Redis,
) -> List[BaseEffect]:
    """Treasurer automatically pays based on evaluation results"""
    evaluation_score = result.get("score", 0)
    target_agent = parameters.get("evaluated_agent")

    if not target_agent:
        logger.error("treasurer_payment missing target agent")
        return []

    if evaluation_score >= 0.8:
        amount = 25
        reason = f"Excellent performance (score: {evaluation_score:.2f})"
    elif evaluation_score >= 0.6:
        amount = 15
        reason = f"Good performance (score: {evaluation_score:.2f})"
    elif evaluation_score >= 0.4:
        amount = 10
        reason = f"Satisfactory performance (score: {evaluation_score:.2f})"
    else:
        logger.info(f"No payment for {target_agent} due to low score: {evaluation_score}")
        return []

    return [
        CallTool(
            conversation_id=conversation_id,
            agent_id="treasurer",
            branch_id=stack.current_branch(),
            tool_name="transfer_funds",
            parameters={"to_agent": target_agent, "amount": amount, "reason": reason},
            tool_call_id=f"treasurer_payment_{target_agent}_{evaluation_score}",
            tool_state_env={},
        )
    ]


@register_post_effect("save_artifact")
def _save_artifact_noop(**_kwargs) -> List[BaseEffect]:
    """Placeholder for artifact saving"""
    logger.debug("save_artifact post-effect not implemented yet – no-op")
    return []


@register_post_effect("raise_event")
def _raise_event_noop(**_kwargs) -> List[BaseEffect]:
    """Placeholder for event raising"""
    logger.debug("raise_event post-effect not implemented yet – no-op")
    return []
