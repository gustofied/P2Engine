from dataclasses import dataclass
from typing import Optional

from .base import BaseState


@dataclass(slots=True, frozen=True)
class UserMessageState(BaseState):
    text: str
    meta: Optional[str] = None
