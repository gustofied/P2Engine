from dataclasses import dataclass
from typing import Any, Dict

from .base import BaseState


@dataclass(slots=True, frozen=True)
class ToolCallState(BaseState):
    id: str
    function_name: str
    arguments: Dict[str, Any]
