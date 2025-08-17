from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import redis

from infra.logging.logging_config import logger
from infra.logging.metrics import metrics
from orchestrator.registries import ToolRegistry
from runtime.effects import CallTool
from runtime.helpers import _hash_tool_call  

__all__ = [
    "BaseDedupPolicy",
    "NoDedupPolicy",
    "PenaltyDedupPolicy",
    "StrictDedupPolicy",
]

class BaseDedupPolicy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @abstractmethod
    def should_execute(self, effect: CallTool) -> bool: ...



class NoDedupPolicy(BaseDedupPolicy):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        pass

    @property
    def name(self) -> str:
        return "none"

    def should_execute(self, effect: CallTool) -> bool:
        return True


def _dedup_key(effect: CallTool) -> str:
    stable_hash = _hash_tool_call(effect.tool_name, effect.parameters)
    return f"dedup:{effect.conversation_id}:{effect.agent_id}:" f"{effect.branch_id}:{stable_hash}"


class PenaltyDedupPolicy(BaseDedupPolicy):
    def __init__(
        self,
        redis_client: redis.Redis,
        tool_registry: ToolRegistry,
        ttl: int = 86_400,
    ) -> None:
        self.redis = redis_client
        self.tools = tool_registry
        self.ttl = ttl

    @property
    def name(self) -> str:
        return "penalty"

    def should_execute(self, effect: CallTool) -> bool:
        tool = self.tools.get_tool_by_name(effect.tool_name)
        ttl = (tool.config.dedup_ttl if tool else None) or self.ttl

        added = self.redis.set(_dedup_key(effect), "1", ex=ttl, nx=True)
        if not added:
            metrics.emit(
                "duplicate_tool_call",
                1,
                tags={
                    "conversation_id": effect.conversation_id,
                    "agent_id": effect.agent_id,
                    "tool": effect.tool_name,
                    "branch": effect.branch_id,
                    "policy": self.name,
                    "action": "allowed",
                },
            )
            logger.info("Duplicate tool call (penalty, allowed): %s", effect.tool_name)
        return True


class StrictDedupPolicy(BaseDedupPolicy):
    def __init__(
        self,
        redis_client: redis.Redis,
        tool_registry: ToolRegistry,
        ttl: int = 86_400,
    ) -> None:
        self.redis = redis_client
        self.tools = tool_registry
        self.ttl = ttl

    @property
    def name(self) -> str:
        return "strict"

    def should_execute(self, effect: CallTool) -> bool:
        tool = self.tools.get_tool_by_name(effect.tool_name)
        side_effect_free = bool(tool and tool.config.side_effect_free)

        ttl = (tool.config.dedup_ttl if tool else None) or self.ttl
        added = self.redis.set(_dedup_key(effect), "1", ex=ttl, nx=True)

        if added:
            return True 

        action = "allowed" if side_effect_free else "blocked"
        metrics.emit(
            "duplicate_tool_call",
            1,
            tags={
                "conversation_id": effect.conversation_id,
                "agent_id": effect.agent_id,
                "tool": effect.tool_name,
                "branch": effect.branch_id,
                "policy": self.name,
                "action": action,
            },
        )
        logger.info("Duplicate tool call (%s): %s", action, effect.tool_name)
        return side_effect_free
