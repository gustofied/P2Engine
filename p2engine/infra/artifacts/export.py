from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable, List, Optional

from infra.artifacts.bus import get_bus
from infra.evals.aggregate import best_branch, branch_score


# --------------------------------------------------------------------------- #
# helpers
# --------------------------------------------------------------------------- #
def _iter_branch_states(session_id: str, branch_id: str) -> Iterable[Dict]:
    """Yield every (header,payload) pair for the given branch – newest-first."""
    bus = get_bus()
    idx_key = f"artifacts:{session_id}:index"
    for ref, raw in bus.redis.hscan_iter(idx_key):
        hdr = json.loads(raw)
        if hdr.get("branch_id") != branch_id:
            continue
        payload = bus.driver.read_payload(session_id, ref, hdr["mime"])
        yield {"ref": ref, "header": hdr, "payload": payload}


# --------------------------------------------------------------------------- #
# public API
# --------------------------------------------------------------------------- #
def export_trajectories(
    session_id: str,
    *,
    min_score: float = 0.8,
    branch_policy: str = "best",  # "best" | "all" | branch_id
    include_evals: bool = True,  # reserved for future
    eval_metric: str = "score",
    format: str = "jsonl",
    out_path: Optional[str] = None,
):
    """
    Dump every branch trajectory that reaches `min_score`.

    Returns an iterator if `out_path` is None, else writes to disk.
    """
    bus = get_bus()

    # ---- which branches? ----------------------------------------------------
    if branch_policy == "best":
        branch_ids: List[str] = []
        bid = best_branch(session_id, metric=eval_metric)
        if bid:
            branch_ids.append(bid)
    elif branch_policy == "all":
        branch_ids = sorted({hdr["branch_id"] for hdr, _ in bus.evaluations_for(session_id)})
    else:
        branch_ids = [branch_policy]

    # ---- gather -------------------------------------------------------------
    trajs: List[Dict] = []
    for bid in branch_ids:
        score = branch_score(session_id=session_id, branch_id=bid, metric=eval_metric) or 0.0
        if score < min_score:
            continue
        trajs.append(
            {
                "session_id": session_id,
                "branch_id": bid,
                "score": score,
                "states": list(_iter_branch_states(session_id, bid)),
            }
        )

    # ---- emit ---------------------------------------------------------------
    if format != "jsonl":
        raise ValueError("only jsonl output is supported right now")

    if out_path is None:
        # generator style
        for row in trajs:
            yield row
    else:
        p = Path(out_path)
        with p.open("w", encoding="utf-8") as fh:
            for row in trajs:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
        return str(p)
