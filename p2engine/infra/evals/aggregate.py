from __future__ import annotations

from typing import Optional

from infra.artifacts.bus import get_bus
from infra.evals.metrics import mean_metric


def branch_score(
    *,
    session_id: str,
    branch_id: str,
    metric: str = "score",
) -> Optional[float]:
    """
    Compute the average of the requested metric for all evaluation artefacts
    attached to the (session, branch). Returns *None* if no evaluations exist.
    """
    bus = get_bus()
    evals = bus.evaluations_for(session_id, branch_id=branch_id)
    if not evals:
        return None

    values = []
    for hdr, _payload in evals:
        if metric == "score":
            if hdr.get("score") is not None:
                values.append(float(hdr["score"]))
        else:
            meta = hdr.get("meta", {})
            metrics = meta.get("eval_metrics", {})
            if metric in metrics:
                values.append(float(metrics[metric]))

    return mean_metric(values)


def best_branch(session_id: str, metric: str = "score") -> Optional[str]:
    """
    Return the branch_id with the **highest** average value for the given
    metric. If no evaluations exist, returns *None*.
    """
    bus = get_bus()
    branches = set(hdr["branch_id"] for hdr, _ in bus.evaluations_for(session_id))
    best_bid = None
    best_val = float("-inf")
    for bid in branches:
        val = branch_score(session_id=session_id, branch_id=bid, metric=metric)
        if val is not None and val > best_val:
            best_val = val
            best_bid = bid
    return best_bid
