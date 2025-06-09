from dataclasses import dataclass

from .base import BaseState


@dataclass(slots=True, frozen=True)
class AgentCallState(BaseState):
    agent_id: str
    message: str
