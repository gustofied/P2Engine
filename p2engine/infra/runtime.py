"""
infra/runtime.py
Deprecated duplicate of AgentRuntime that lived in `infra/`.

It now re-exports the canonical implementation from runtime.agent_runtime so
imports keep working while the codebase is cleaned up.
"""

from runtime.agent_runtime import AgentRuntime  # noqa: F401

__all__ = ["AgentRuntime"]
