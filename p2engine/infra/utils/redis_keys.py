"""Central place for Redis key helpers.
Keeping all key‑format rules here avoids drift across modules.
"""

from __future__ import annotations

__all__ = [
    "event_sequence_key",
    "dedup_key",
]


def event_sequence_key(conversation_id: str, agent_id: str) -> str:
    """Sequence counter for (conversation, agent)."""
    return f"conversation:{conversation_id}:{agent_id}:event_sequence"


def dedup_key(conversation_id: str, agent_id: str) -> str:
    """Generic per‑agent deduplication key used by push_* effects."""
    return f"stack:{conversation_id}:{agent_id}:dedup"
