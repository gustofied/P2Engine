from __future__ import annotations

import redis
from celery import Celery
from typing import List, TYPE_CHECKING

from infra.logging.logging_config import logger
from infra.logging.metrics import metrics
from orchestrator.interactions.states.tool_result import ToolResultState
from orchestrator.interactions.states.waiting import WaitingState
from runtime.effects import BaseEffect, CallTool
from runtime.policies.dedup import BaseDedupPolicy

if TYPE_CHECKING:  # runtime-safe type hints
    from orchestrator.interactions.stack import InteractionStack


def _settle_wait(stack, corr_id: str) -> None:
    """
    Pop the top WaitingState if it matches the given correlation-id.
    (Importing InteractionStack is deferred to avoid circular imports.)
    """
    cur = stack.current()
    if cur and isinstance(cur.state, WaitingState) and cur.state.correlation_id == corr_id:
        stack.pop()


class EffectExecutor:
    """
    Dispatches runtime.effects.BaseEffect objects and handles deduplication.
    """

    def __init__(
        self,
        redis_client: redis.Redis,
        celery_app: Celery,
        dedup_policy: BaseDedupPolicy,
    ) -> None:
        self.redis = redis_client
        self.celery = celery_app
        self.dedup_policy = dedup_policy

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def execute(self, effects: List[BaseEffect], conversation_id: str) -> None:
        """
        Iterate through a list of effects and execute / enqueue them.
        """
        from infra.logging.effect_log import append_effect_log  # local import OK

        for eff in effects:
            # ── tool calls with deduplication ─────────────────────────────
            if isinstance(eff, CallTool) and not self.dedup_policy.should_execute(eff):
                self._skip_duplicate_tool_call(eff, conversation_id)
                continue

            if isinstance(eff, CallTool):
                self._enqueue_tool(eff, conversation_id)
                continue

            # ── generic effect ────────────────────────────────────────────
            try:
                eff.execute(self.redis, self.celery)
                logger.info(
                    {
                        "message": "Effect executed",
                        "effect": type(eff).__name__,
                        "conversation_id": conversation_id,
                    }
                )
                metrics.emit("effect_executed", 1, tags={"effect": type(eff).__name__})
            except Exception as exc:
                logger.error(
                    {
                        "message": "Failed to execute effect",
                        "effect": type(eff).__name__,
                        "conversation_id": conversation_id,
                        "error": str(exc),
                    },
                    exc_info=True,
                )

    # ------------------------------------------------------------------ #
    # Internals
    # ------------------------------------------------------------------ #

    def _skip_duplicate_tool_call(self, eff: CallTool, conversation_id: str) -> None:
        """
        Mark a duplicate tool-call as skipped and settle the waiting frame.
        """
        from infra.logging.effect_log import append_effect_log
        from orchestrator.interactions.stack import InteractionStack
        from runtime.tasks.tasks import enqueue_session_tick

        append_effect_log(
            conversation_id,
            {
                "branch_id": eff.branch_id,
                "tool_name": eff.tool_name,
                "parameters": eff.parameters,
                "meta": {"status": "skipped", "reason": "dedup"},
            },
        )

        stack = InteractionStack(self.redis, conversation_id, eff.agent_id)
        _settle_wait(stack, eff.tool_call_id)

        stack.push(
            ToolResultState(
                tool_call_id=eff.tool_call_id,
                tool_name=eff.tool_name,
                result={
                    "status": "skipped",
                    "message": "Duplicate call skipped by dedup policy",
                },
            )
        )
        enqueue_session_tick(conversation_id)

        logger.debug(
            {
                "message": "Skipped duplicate tool call",
                "tool": eff.tool_name,
                "conversation_id": conversation_id,
            }
        )
        metrics.emit(
            "effect_skipped",
            1,
            tags={"effect": type(eff).__name__, "reason": "dedup"},
        )

    def _enqueue_tool(self, eff: CallTool, conversation_id: str) -> None:
        """
        Serialize a tool call into the Celery ‘tools’ queue.
        """
        from infra.logging.interaction_log import log_interaction_event

        log_interaction_event(
            conversation_id=eff.conversation_id,
            event_type="tool_call",
            agent_id=eff.agent_id,
            correlation_id=eff.tool_call_id,
            payload={"tool_name": eff.tool_name, "parameters": eff.parameters},
        )

        self.celery.send_task(
            "runtime.tasks.tasks.execute_tool",
            args=[
                conversation_id,
                eff.agent_id,
                eff.tool_name,
                eff.parameters,
                eff.tool_call_id,
                eff.branch_id,
                eff.tool_state_env or {},
            ],
            queue="tools",
        )

        logger.info(
            {
                "message": "Effect executed (tool scheduled)",
                "effect": "CallTool",
                "tool": eff.tool_name,
                "conversation_id": conversation_id,
            }
        )
        metrics.emit("effect_executed", 1, tags={"effect": "CallTool"})
