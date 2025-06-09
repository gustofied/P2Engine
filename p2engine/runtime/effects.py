from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass
from typing import Any, Dict, Optional, TYPE_CHECKING

import redis

from infra.logging.logging_config import logger
from orchestrator.interactions.states.agent_result import AgentResultState
from orchestrator.interactions.states.user_message import UserMessageState
from orchestrator.interactions.states.waiting import WaitingState

# ────────────────────────────────────────────────────────────────────
#  Forward‑refs for *typing only* to prevent runtime import cycles
# ────────────────────────────────────────────────────────────────────
if TYPE_CHECKING:  # pragma: no cover
    from orchestrator.interactions.stack import InteractionStack  # noqa: F401
    from infra.session import get_session  # noqa: F401

__all__ = [
    "BaseEffect",
    "CallTool",
    "PushToAgent",
    "PublishSystemReply",
    "PushAgentResult",
]


# ────────────────────────────────────────────────────────────────────
#  Helpers
# ────────────────────────────────────────────────────────────────────


def _get_celery_app():
    """Lazy import so `celery_app` isn’t pulled in at module load time."""
    from runtime.tasks.celery_app import app as celery_app  # local import

    return celery_app


# --------------------------------------------------------------------
# Base class
# --------------------------------------------------------------------
@dataclass(slots=True, frozen=True)
class BaseEffect:  # noqa: D401 – one‑liner docs are fine here
    """Abstract parent for all side‑effects."""

    def _stable_blob(self) -> str:
        return json.dumps(asdict(self), default=str, sort_keys=True)

    def dedup_key(self) -> str:
        return hashlib.sha1(self._stable_blob().encode()).hexdigest()  # nosec B303

    def execute(self, redis_client: redis.Redis, celery_app=None) -> None:  # noqa: D401
        """Execute the effect – subclasses must override."""
        raise NotImplementedError


# --------------------------------------------------------------------
# Push message to another agent
# --------------------------------------------------------------------
@dataclass(slots=True, frozen=True)
class PushToAgent(BaseEffect):
    conversation_id: str
    target_agent_id: str
    message: str
    sender_agent_id: str
    correlation_id: str
    _TTL_SEC: int = 86_400

    def execute(self, redis_client: redis.Redis, celery_app=None) -> None:  # noqa: C901 – keep long for clarity
        # lazy import to avoid import‑time cycle with infra.session
        from infra.session import get_session  # local
        from infra.logging.interaction_log import log_interaction_event

        log_interaction_event(
            conversation_id=self.conversation_id,
            event_type="agent_call",
            agent_id=self.sender_agent_id,
            correlation_id=self.correlation_id,
            payload={
                "target_agent_id": self.target_agent_id,
                "message": self.message,
            },
        )

        session = get_session(self.conversation_id, redis_client)
        stack = session.stack_for(self.target_agent_id)

        # propagate episode id from parent → child so metrics are grouped
        parent_episode_id = redis_client.get(f"stack:{self.conversation_id}:{self.sender_agent_id}:episode:{stack.current_branch()}")
        if parent_episode_id:
            redis_client.set(
                f"stack:{self.conversation_id}:{self.target_agent_id}:episode:{stack.current_branch()}",
                parent_episode_id,
                ex=86_400,
            )

        stack.push(UserMessageState(text=self.message))

        redis_client.setex(
            f"child_to_parent:{self.conversation_id}:{self.target_agent_id}",
            self._TTL_SEC,
            self.sender_agent_id,
        )
        redis_client.setex(
            f"agent_call_correlation:{self.conversation_id}:{self.target_agent_id}",
            self._TTL_SEC,
            self.correlation_id,
        )

        (celery_app or _get_celery_app()).send_task(
            "runtime.tasks.tasks.process_session_tick",
            args=[self.conversation_id],
            queue="ticks",
        )

        logger.info(
            {
                "message": "Pushed message to agent",
                "conversation_id": self.conversation_id,
                "target_agent_id": self.target_agent_id,
                "sender_agent_id": self.sender_agent_id,
            }
        )


# --------------------------------------------------------------------
# Child agent returns a result
# --------------------------------------------------------------------
@dataclass(slots=True, frozen=True)
class PushAgentResult(BaseEffect):
    conversation_id: str
    target_agent_id: str
    correlation_id: str
    result: Dict[str, Any]
    child_agent_id: str
    score: Optional[float] = None

    def execute(self, redis_client: redis.Redis, celery_app=None) -> None:  # noqa: C901 – keep long for clarity
        guard_key = f"expect_agent_result:{self.conversation_id}:{self.target_agent_id}:{self.correlation_id}"
        if not redis_client.exists(guard_key):
            logger.warning(
                {
                    "message": "late_agent_result_missing_parent",
                    "conversation_id": self.conversation_id,
                    "target_agent_id": self.target_agent_id,
                    "child_agent_id": self.child_agent_id,
                    "correlation_id": self.correlation_id,
                }
            )
            return

        # local import avoids cycle
        from orchestrator.interactions.stack import InteractionStack  # local
        from infra.logging.interaction_log import log_interaction_event

        stack = InteractionStack(redis_client, self.conversation_id, self.target_agent_id)

        # pop WaitingState if it matches
        top = stack.current()
        if isinstance(top.state, WaitingState) and top.state.correlation_id == self.correlation_id:
            stack.pop()

        redis_client.delete(guard_key)

        duplicate = any(
            isinstance(e.state, AgentResultState) and e.state.correlation_id == self.correlation_id for e in stack.iter_last_n(50)
        )

        log_interaction_event(
            conversation_id=self.conversation_id,
            event_type="agent_result",
            agent_id=self.child_agent_id,
            correlation_id=self.correlation_id,
            payload={
                "result": self.result,
                "score": self.score,
                "target_agent_id": self.target_agent_id,
            },
        )

        if not duplicate:
            payload: Dict[str, Any] = dict(self.result)
            if self.score is not None:
                payload["score"] = self.score
            stack.push(
                AgentResultState(
                    correlation_id=self.correlation_id,
                    result=payload,
                    score=self.score,
                )
            )

        (celery_app or _get_celery_app()).send_task(
            "runtime.tasks.tasks.process_session_tick",
            args=[self.conversation_id],
            queue="ticks",
        )

        # clean aux keys
        redis_client.delete(f"child_to_parent:{self.conversation_id}:{self.child_agent_id}")
        redis_client.delete(f"agent_call_correlation:{self.conversation_id}:{self.child_agent_id}")

        logger.info(
            {
                "message": "Pushed agent result to parent agent",
                "conversation_id": self.conversation_id,
                "target_agent_id": self.target_agent_id,
                "child_agent_id": self.child_agent_id,
                "score": self.score,
            }
        )


# --------------------------------------------------------------------
# Tool execution scheduling
# --------------------------------------------------------------------
@dataclass(slots=True, frozen=True)
class CallTool(BaseEffect):
    conversation_id: str
    agent_id: str
    branch_id: str
    tool_name: str
    parameters: dict
    tool_call_id: str
    tool_state_env: dict

    def execute(self, redis_client: redis.Redis, celery_app=None) -> None:
        (celery_app or _get_celery_app()).send_task(
            "runtime.tasks.tasks.execute_tool",
            args=[
                self.conversation_id,
                self.agent_id,
                self.tool_name,
                self.parameters,
                self.tool_call_id,
                self.branch_id,
                self.tool_state_env,
            ],
            queue="tools",
        )
        logger.info(
            {
                "message": "Scheduled tool",
                "conversation_id": self.conversation_id,
                "tool": self.tool_name,
            }
        )


# --------------------------------------------------------------------
# Publish a system‑level reply
# --------------------------------------------------------------------
@dataclass(slots=True, frozen=True)
class PublishSystemReply(BaseEffect):
    conversation_id: str
    message: str

    def dedup_key(self) -> str:  # unique every time – include timestamp
        return hashlib.sha1(f"{self.conversation_id}:{time.time_ns()}".encode()).hexdigest()  # nosec B303

    def execute(self, redis_client: redis.Redis, celery_app=None) -> None:
        redis_client.set(f"response:{self.conversation_id}", self.message, ex=3_600)
        logger.info({"message": "system_reply_published", "conversation_id": self.conversation_id})
