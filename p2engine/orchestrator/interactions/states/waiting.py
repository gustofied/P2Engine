from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Literal, Optional

from .base import BaseState

WaitingKind = Literal["llm", "tool", "agent", "user_input"]


@dataclass(slots=True, frozen=True)
class WaitingState(BaseState):
    """
    A transient state telling the runtime we are waiting for an external edge
    (LLM stream, tool execution, human reply, …).

    * `deadline` is an absolute wall-clock epoch (time.time()) after which the
      wait is considered expired.
    * `correlation_id` lets the executor match the eventual result or detect
      duplicate requests.
    """

    kind: WaitingKind
    deadline: float
    correlation_id: Optional[str] = None


    def remaining(self, now: float | None = None) -> float:
        """
        Seconds until the deadline. Negative → already expired.
        """
        if now is None:
            now = time.time()
        return self.deadline - now

    def is_expired(self, now: float | None = None) -> bool:
        return self.remaining(now) <= 0

    def age(self, entry_ts: float, now: float | None = None) -> float:
        """
        How long this state has been sitting on the stack.

        Uses the `StackEntry.ts` provided by the caller so that offline replay
        (or time-travel debugging) stays deterministic.
        """
        if now is None:
            now = time.time()
        return now - entry_ts
