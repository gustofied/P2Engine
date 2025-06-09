from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from .base import BaseState


@dataclass(slots=True, frozen=True)
class AssistantMessageState(BaseState):
    content: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    meta: Optional[str] = None
