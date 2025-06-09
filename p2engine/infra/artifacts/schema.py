from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional, TypedDict


class ArtifactMeta(TypedDict, total=False):
    state_cls: Optional[str]
    tags: list[str]
    # --- evaluator additions -------------------------------------------------
    eval_metrics: dict[str, float]  # individual metric → value
    status: Literal["pending", "finished"]  # evaluation status
    # ------------------------------------------------------------------------


class ArtifactHeader(TypedDict, total=False):
    # ─── core routing --------------------------------------------------------
    ref: str
    session_id: str
    branch_id: str
    episode_id: str
    group_id: Optional[str]
    step_idx: int
    parent_refs: list[str]

    # ─── semantics -----------------------------------------------------------
    role: Literal[
        "state",
        "tool_call",
        "tool_result",
        "evaluation",  # NEW
        "policy_decision",
        "metrics",
    ]
    if TYPE_CHECKING:  # mypy friendliness
        type: Literal["state", "tool_call", "tool_result", "evaluation", "event"]

    # ─── scoring / search helpers -------------------------------------------
    score: Optional[float]
    reward: Optional[float]
    visit_count: Optional[int]
    value_estimate: Optional[float]

    # ─── provenance ----------------------------------------------------------
    agent_id: str
    policy_id: Optional[str]
    model: Optional[str]
    cost_usd: Optional[float]
    latency_ms: Optional[int]
    prompt_tokens: Optional[int]
    completion_tokens: Optional[int]

    # ─── persistence metadata -----------------------------------------------
    compressed: Optional[bool]
    raw_len: Optional[int]
    mime: str
    ts: str
    state_id: str
    meta: ArtifactMeta

    # ─── evaluator additions -------------------------------------------------
    evaluator_id: Optional[str]  # which judge was used
    judge_version: Optional[str]  # semantic version of the judge
    # ------------------------------------------------------------------------


# ──────────────────────────────────────────────────────────────────────────────
# helper utilities
# ──────────────────────────────────────────────────────────────────────────────
def generate_ref() -> str:
    """Return a random, URL-safe reference ID (32-hex char)."""
    return uuid.uuid4().hex


def current_timestamp() -> str:
    """UTC timestamp with millisecond precision and explicit “Z” suffix."""
    return datetime.utcnow().isoformat(timespec="milliseconds") + "Z"


def parse_timestamp(ts: str) -> float:
    """Convert an ISO-8601 timestamp back into a Unix epoch (float seconds)."""
    return datetime.fromisoformat(ts.replace("Z", "+00:00")).timestamp()
