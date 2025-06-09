from dataclasses import dataclass

from .base import BaseState


@dataclass(slots=True, frozen=True)
class UserResponseState(BaseState):
    text: str
