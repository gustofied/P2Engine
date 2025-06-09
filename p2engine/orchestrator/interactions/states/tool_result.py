from dataclasses import dataclass
from typing import Any, Dict, Optional
from .base import BaseState


@dataclass(slots=True, frozen=True)
class ToolResultState(BaseState):
    """
    Result of a tool call.

    Phase-2 adds the optional `reward` field so we can attach a simple scalar
    credit (1 = success, 0 = failure/timeout) for later RL or critic training.
    """

    tool_call_id: str
    tool_name: str
    result: Dict[str, Any]
    arguments: Optional[Dict[str, Any]] = None
    reward: Optional[float] = None
