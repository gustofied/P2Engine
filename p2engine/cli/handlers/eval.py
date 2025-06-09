from __future__ import annotations

from typing import List, Tuple

from infra.artifacts.bus import get_bus
from infra.artifacts.schema import ArtifactHeader
from infra.evals.aggregate import branch_score


def best_branches(session_id: str, k: int = 20, metric: str = "score") -> List[Tuple[str, float]]:
    """
    Return top-k branch_id → aggregated score, sorted desc.
    """
    bus = get_bus()
    branches = {hdr["branch_id"] for hdr, _ in bus.evaluations_for(session_id) if hdr.get("role") == "evaluation"}
    scored = [(bid, branch_score(session_id=session_id, branch_id=bid, metric=metric)) for bid in branches]
    scored = [(b, s) for b, s in scored if s is not None]
    scored.sort(key=lambda t: t[1], reverse=True)
    return scored[:k]


def eval_diff(ref_a: str, ref_b: str) -> Tuple[ArtifactHeader, ArtifactHeader]:
    """
    Return the two evaluation headers – caller prints the JSON diff.
    """
    bus = get_bus()
    h1, _ = bus.get(ref_a)
    h2, _ = bus.get(ref_b)
    return h1, h2
