# infra/session.py
from __future__ import annotations

import threading
from typing import Dict, Optional

import redis

from infra.logging.logging_config import logger
from orchestrator.interactions.stack import InteractionStack
from orchestrator.interactions.states.user_message import UserMessageState
from orchestrator.interactions.states.finished import FinishedState

__all__ = ["Session", "get_session"]

_thread_local = threading.local()


class Session:
    """Lightweight wrapper around Redis-backed conversation state."""

    def __init__(self, conv_id: str, redis_client: redis.Redis):
        self.id = conv_id
        self.redis = redis_client
        self._tick: Optional[int] = None
        self._agents: set[str] = set(self.redis.smembers(f"session:{self.id}:agents"))
        self._stacks: Dict[str, InteractionStack] = {}

    def register_agent(self, agent_id: str) -> None:
        if agent_id not in self._agents:
            self._agents.add(agent_id)
            self.redis.sadd(f"session:{self.id}:agents", agent_id)
            if not self.redis.sismember("active_sessions", self.id):
                self.redis.sadd("active_sessions", self.id)
                logger.info(
                    {
                        "message": "Session registered in active_sessions",
                        "session_id": self.id,
                        "agent_id": agent_id,
                    }
                )

    def unregister_agent(self, agent_id: str, *, force: bool = False) -> None:
        if not force:
            logger.debug(
                {
                    "message": "Soft-unregister ignored – agent kept alive",
                    "session_id": self.id,
                    "agent_id": agent_id,
                }
            )
            return
        if agent_id in self._agents:
            self._agents.remove(agent_id)
            self.redis.srem(f"session:{self.id}:agents", agent_id)
            self._maybe_finish()

    @property
    def tick(self) -> int:
        if self._tick is None:
            raw = self.redis.get(f"session:{self.id}:tick")
            self._tick = int(raw) if raw else 0
        return self._tick

    def refresh_tick(self) -> int:
        self._tick = None
        return self.tick

    def stack_for(self, agent_id: str) -> InteractionStack:
        if agent_id not in self._stacks:
            self._stacks[agent_id] = InteractionStack(self.redis, self.id, agent_id)
            self.register_agent(agent_id)

        stack = self._stacks[agent_id]
        stack.refresh_current_branch()

        if stack.length() == 0:
            prev = stack.current(branch_id="main")
            if not (prev and isinstance(prev.state, FinishedState)):
                stack.push(UserMessageState(text="<!-- synthetic seed -->"))

        return stack

    def save(self) -> None:
        if self._tick is not None:
            self.redis.set(f"session:{self.id}:tick", self._tick)

    def _maybe_finish(self) -> None:
        if not self.redis.smembers(f"session:{self.id}:agents"):
            self.redis.srem("active_sessions", self.id)
            logger.info(
                {
                    "message": "Session finished – no live agents",
                    "session_id": self.id,
                }
            )

    def __repr__(self) -> str:  # pragma: no cover
        return f"<Session {self.id} tick={self.tick}>"

    def __enter__(self) -> "Session":
        return self

    def __exit__(self, *_exc) -> None:
        self.save()


def get_session(conv_id: str, redis_client: redis.Redis) -> "Session":
    """Return the per-thread singleton *Session* for *conv_id*."""

    if not hasattr(_thread_local, "sessions"):
        _thread_local.sessions = {}

    if conv_id in _thread_local.sessions:
        sess: Session = _thread_local.sessions[conv_id]
        if sess.redis is not redis_client:
            logger.debug(
                {
                    "message": "Reusing existing Session despite different Redis client",
                    "session_id": conv_id,
                }
            )
        return sess

    sess = Session(conv_id, redis_client)
    _thread_local.sessions[conv_id] = sess
    return sess
