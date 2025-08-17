from __future__ import annotations
from dataclasses import dataclass
from typing import ClassVar


@dataclass(slots=True, frozen=True)
class BaseState:
    """
    Base type for all interaction-stack state objects.

    `__version__` is used when (de)serialising; we no longer keep an *instance*
    field called `version`, because that breaks dataclass inheritance rules.
    """

    __version__: ClassVar[int] = 1  
