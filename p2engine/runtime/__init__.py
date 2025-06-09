"""
runtime package bootstrap

Only declare the public sub-packages here; DO NOT import heavy
modules at import-time – that can create circular-import traps
(e.g. the former `from . import handlers` line).

Anything that needs `runtime.handlers` (or other internals) should
`import runtime.handlers` *inside the function that uses it* or at
the very end of its own module.
"""

__all__ = [
    "engine",
    "event_bus",
    "notification_consumer",
    "processes",
    "system",
    "system_manager",
    "task_runner",
]

# ─────────────────────────────────────────────────────────────────────────────
# NOTE:
#   The eager `from . import handlers` that lived here created a circular
#   dependency:
#     orchestrator.interactions.stack  →  runtime.constants
#       ↳ runtime.__init__  →  runtime.handlers  →  … →  stack
#
#   Removing that line keeps `runtime` lightweight and import-safe.
# ─────────────────────────────────────────────────────────────────────────────
