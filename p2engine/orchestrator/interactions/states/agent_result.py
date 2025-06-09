from dataclasses import dataclass
from typing import Any, Dict, Optional
from .base import BaseState


@dataclass(slots=True, frozen=True)
class AgentResultState(BaseState):
    """
    Result a child-agent sends back to its parent.

    * `result`  – the child’s payload (usually its assistant-style answer)
    * `score`   – optional holistic evaluation score injected later
                  (e.g. by the GPT-4 judge in runtime/tasks/evals.py)
    """

    correlation_id: str
    result: Dict[str, Any]
    score: Optional[float] = None
