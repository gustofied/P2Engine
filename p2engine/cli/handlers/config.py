from __future__ import annotations

import json
from pathlib import Path
from typing import List

# ── existing helpers ──────────────────────────────────────────────────────────


def set_delivery(engine, scope: str, key: str, mode: str):
    r = engine.container.get_redis_client()
    if scope == "conversation":
        r.set(f"conversation:{key}:delivery", mode)
    elif scope == "system":
        r.set(f"system:{key}:delivery", mode)
    elif scope == "process":
        r.set(f"process:{key}:delivery", mode)
    else:
        raise ValueError("invalid_scope")


def set_override(engine, conv_id: str, agent_id: str, patch: dict):
    r = engine.container.get_redis_client()
    key = f"agent:{agent_id}:{conv_id}:override"
    override = json.loads(r.get(key) or "{}")
    override.update(patch)
    r.set(key, json.dumps(override), ex=604_800)


def get_overrides(engine, conv_id: str, agent_id: str) -> dict:
    r = engine.container.get_redis_client()
    raw = r.get(f"agent:{agent_id}:{conv_id}:override")
    return json.loads(raw) if raw else {}


# ── NEW helper utilities for CLI autocompletion ──────────────────────────────


def _bytes_or_str(v):
    return v if isinstance(v, str) else v.decode(errors="replace")


def get_conversation_names(engine) -> List[str]:
    """
    Return a sorted list of conversation names
    (the human-friendly label, *not* the UUID id).
    """
    r = engine.container.get_redis_client()
    names: List[str] = []
    for key in r.keys("conversation:*:id"):
        conv_name = _bytes_or_str(key).split(":", 2)[1]
        names.append(conv_name)
    return sorted(names)


def get_tool_names(engine) -> List[str]:
    """
    List all registered tool names from the global `ToolRegistry`.
    """
    registry = engine.container.get_tool_registry()
    return sorted(tool.name for tool in registry.get_tools())


def get_persona_names() -> List[str]:
    """
    Scan `agents/templates/personas/` for `*.j2` templates and
    return their stem names – used by `config set-behavior`.
    """
    templates_dir = Path(__file__).resolve().parent.parent.parent / "agents" / "templates" / "personas"
    if not templates_dir.exists():
        return []
    return sorted(p.stem for p in templates_dir.glob("*.j2"))
