from dataclasses import dataclass
from typing import ClassVar

from .base import BaseState


@dataclass(slots=True, frozen=True)
class FinishedState(BaseState):
    """
    Terminal marker for an interaction branch.

    The class-level ``is_terminal`` flag makes it inexpensive for
    downstream code to test for “done” without an ``isinstance`` check,
    and it is copied into the artifact header by ``InteractionStack``.
    """

    is_terminal: ClassVar[bool] = True
