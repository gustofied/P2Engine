from __future__ import annotations

from importlib import import_module
from types import ModuleType
from typing import TYPE_CHECKING

from .spec import RolloutSpec
from .expander import expand_variants

__all__ = ["RolloutSpec", "expand_variants", "run_rollout"]


def _lazy_engine() -> ModuleType:
    return import_module("runtime.rollout.engine")


def run_rollout(*args, **kwargs):
    return _lazy_engine().run_rollout(*args, **kwargs)


if TYPE_CHECKING: 
    from runtime.rollout.engine import run_rollout as run_rollout
