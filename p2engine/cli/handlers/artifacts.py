from __future__ import annotations

import json
from typing import List, Tuple

from infra.artifacts.bus import get_bus
from infra.artifacts.schema import ArtifactHeader


def _render_row(idx: int, header: ArtifactHeader, payload) -> str:
    ts = header["ts"]
    kind = header["type"]
    branch = header["branch_id"]
    preview = str(payload)
    if len(preview) > 60:
        preview = preview[:57] + "…"
    return f"{idx:>3}. {ts}  {kind:<12}  br={branch:<8}  {preview}"


# ------------------------------------------------------------------ #
# CLI helpers
# ------------------------------------------------------------------ #
def show_artifacts(
    engine,
    conversation_id: str,
    *,
    branch_id: str | None = None,
    limit: int = 50,
    tag: str | None = None,
    since: str | None = None,
) -> None:
    """List artifacts with optional filters."""
    bus = get_bus()

    results: List[Tuple[ArtifactHeader, object]]
    if branch_id or tag or since:
        results = bus.search(
            conversation_id,
            tag=tag,
            since=since,
            limit=limit,
        )
        # branch filter in Python – cheap
        if branch_id:
            results = [pair for pair in results if pair[0]["branch_id"] == branch_id]
    else:
        # fast-path: fall back to timeline read
        results = bus.read_last_n(limit, session_id=conversation_id)

    if not results:
        print("No artifacts match the filters.")
        return

    for idx, (hdr, payload) in enumerate(results, 1):
        print(_render_row(idx, hdr, payload))


def cat_artifact(engine, ref: str) -> None:
    bus = get_bus()
    try:
        header, payload = bus.get(ref)
    except KeyError as exc:
        print(str(exc))
        return

    print(f"# {header['ts']}  ({header['type']})  session={header['session_id']}\n")
    if isinstance(payload, (dict, list)):
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    elif isinstance(payload, (bytes, bytearray)):
        print(f"<{len(payload)} binary bytes>")
    else:
        print(payload)


def diff_artifacts(engine, ref1: str, ref2: str) -> None:
    bus = get_bus()
    try:
        _, p1 = bus.get(ref1)
        _, p2 = bus.get(ref2)
    except KeyError as exc:
        print(str(exc))
        return

    if not (isinstance(p1, (dict, list)) and isinstance(p2, (dict, list))):
        print("Can only diff JSON-serialisable payloads.")
        return

    import difflib

    left = json.dumps(p1, indent=2, ensure_ascii=False).splitlines()
    right = json.dumps(p2, indent=2, ensure_ascii=False).splitlines()

    for line in difflib.unified_diff(left, right, fromfile=ref1, tofile=ref2):
        print(line)
