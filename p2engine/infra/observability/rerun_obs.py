"""
Lightweight Rerun.io observer SDK for P2Engine.
Zero coupling — silently no-ops if Rerun isn't available.

Adds:
- set_time_seconds(...) to drive timeline playback.
- set_time_sequence(...) to use a discrete "sequence" timeline (no 1970!).
- set_time_frame(...) to use an integer "frame" timeline.
- points2d(...) with radii/colors/labels.
- line_strips2d(...) with per-strip colors.
- graph(...) to log GraphNodes/GraphEdges (variant→session→agent).
- text_log(...) for streaming log lines.
"""

from __future__ import annotations

import contextlib
import logging
import os
import time
from typing import Any, Dict, Optional, Tuple, Sequence, List

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# Configuration from environment
# -----------------------------------------------------------------------------
_ENABLED = os.getenv("OBS_ENABLED", "true").lower() == "true"
_RUN_ID = os.getenv("RUN_ID", f"run_{int(time.time())}")
_BACKEND = os.getenv("OBS_BACKEND", "rerun")
_SAMPLE_RATE = float(os.getenv("OBS_SAMPLE", "1.0"))
# default: do NOT spawn viewer (workers will import this)
_SPAWN_DEFAULT = os.getenv("OBS_SPAWN", "0") == "1"

# Internal backend handle: ("rerun", rerun_module) or None
_backend: Optional[Tuple[str, Any]] = None


# -----------------------------------------------------------------------------
# Initialization (idempotent, opt-in)
# -----------------------------------------------------------------------------
def init_if_needed(spawn: Optional[bool] = None, run_id: Optional[str] = None) -> bool:
    """
    Initialize the Rerun backend on-demand (idempotent).

    - spawn: whether to open a viewer window (defaults to OBS_SPAWN)
    - run_id: optional override for the run namespace

    Returns True if the backend was initialized by this call, False otherwise.
    """
    global _backend, _RUN_ID

    if _backend or (not _ENABLED) or (_BACKEND != "rerun"):
        return False

    try:
        import rerun as rr  # type: ignore
    except Exception as e:
        logger.debug("Rerun SDK import failed; observability disabled: %s", e)
        return False

    try:
        if run_id:
            _RUN_ID = run_id
        if spawn is None:
            spawn = _SPAWN_DEFAULT

        recording = f"p2engine:{_RUN_ID}"
        rr.init(recording, spawn=spawn)
        _backend = ("rerun", rr)
        logger.info("Rerun observer initialized: %s (spawn=%s)", recording, spawn)
        return True
    except Exception as e:
        logger.exception("Rerun init failed: %s", e)
        return False


def start_recording(run_id: str, *, spawn: Optional[bool] = None) -> bool:
    """
    Ensure we have an active backend AND switch to a NEW recording for this run_id.
    - If not initialized yet: initializes with this run_id (and optional spawn).
    - If already initialized with a different run_id: attempts rr.new_recording();
      if unavailable, falls back to rr.disconnect()+rr.init(...).
    """
    global _backend, _RUN_ID

    if _backend is None:
        return init_if_needed(spawn=spawn, run_id=run_id)

    if run_id == _RUN_ID:
        return True

    _, rr = _backend
    try:
        target = f"p2engine:{run_id}"
        if hasattr(rr, "new_recording"):
            rr.new_recording(target)  # Rerun ≥ 0.14
        else:
            if hasattr(rr, "disconnect"):
                rr.disconnect()
            rr.init(target, spawn=False)
        _RUN_ID = run_id
        logger.info("Rerun: switched to new recording: %s", target)
        return True
    except Exception as e:
        logger.warning("Rerun: failed to switch to new recording %r: %s", run_id, e)
        return False


def is_active() -> bool:
    return _backend is not None


def current_run_id() -> str:
    return _RUN_ID


# -----------------------------------------------------------------------------
# Path helpers — keep blueprints & logging in sync
# -----------------------------------------------------------------------------
def _path(p: str) -> str:
    p = p.strip("/")
    if p.startswith("runs/"):
        return f"/{p}"
    return f"/runs/{_RUN_ID}/{p}"


def abs_path(p: str) -> str:
    return _path(p)


# -----------------------------------------------------------------------------
# Time helpers — safe no-ops if backend isn't initialized
# -----------------------------------------------------------------------------
def set_time_seconds(timeline: str, t: float) -> None:
    """Set the current time on a named timeline (wall/epoch-like)."""
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.set_time_seconds(timeline, float(t))


def set_time_sequence(timeline: str, step: int | float) -> None:
    """
    Set the current time on a named timeline as a discrete SEQUENCE index.
    This avoids epoch rendering (no more 1970 for step=0).
    """
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.set_time(timeline, sequence=int(step))


def set_time_frame(frame: int | float) -> None:
    """
    Set the current 'frame' timeline to an integer/float index.
    This is great for scrubbing one visual frame per interaction.
    """
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.set_time("frame", sequence=int(frame))


# -----------------------------------------------------------------------------
# Logging helpers — safe no-ops if backend isn't initialized
# -----------------------------------------------------------------------------
def scalar(path: str, value: float, **attrs: Any) -> None:
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.log(_path(path), rr.Scalar(value))


def json_doc(path: str, data: Dict[str, Any], *, timeless: bool = False) -> None:
    """
    Log a JSON document. 'timeless' is accepted for compatibility but ignored
    in the modern Rerun Python API (no 'timeless' kw on rr.log).
    """
    if not _backend:
        return
    _, rr = _backend
    try:
        import json
        rr.log(_path(path), rr.TextDocument(json.dumps(data, indent=2), media_type="application/json"))
    except Exception as e:
        logger.debug("Rerun json_doc failed: %s", e)


def kv(path: str, *, timeless: bool = False, **attrs: Any) -> None:
    """
    Log a small key/value JSON blob. 'timeless' accepted but ignored.
    """
    if not _backend:
        return
    _, rr = _backend
    try:
        import json
        text = json.dumps(attrs, indent=2)
        rr.log(_path(path), rr.TextDocument(text, media_type="application/json"))
    except Exception as e:
        logger.debug("Rerun kv failed: %s", e)


def text_doc(path: str, text: str, *, media_type: str = "text/plain", timeless: bool = False) -> None:
    """
    Log a text document. 'timeless' accepted but ignored.
    """
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.log(_path(path), rr.TextDocument(text, media_type=media_type))


def text_log(path: str, text: str) -> None:
    """Append a single log line to a TextLog entity."""
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.log(_path(path), rr.TextLog(text))


# ---------- Graph primitives (2D) ----------
def points2d(
    path: str,
    positions: Sequence[Sequence[float]],
    *,
    radii: Optional[Sequence[float]] = None,
    colors: Optional[Sequence[Sequence[int]]] = None,  # RGBA 0..255
    labels: Optional[Sequence[str]] = None,
    timeless: bool = False,  # accepted but ignored by rr.log
) -> None:
    """Log 2D points with optional radii/colors/labels."""
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.log(_path(path), rr.Points2D(positions, radii=radii, colors=colors, labels=labels))


def line_strips2d(
    path: str,
    strips: Sequence[Sequence[Sequence[float]]],
    *,
    colors: Optional[Sequence[Sequence[int]]] = None,  # one color per strip
    timeless: bool = False,  # accepted but ignored by rr.log
) -> None:
    """
    Log 2D line strips; each strip is a list of [x,y] points.
    For edges, pass 2-point strips: [[x1,y1],[x2,y2]].
    """
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.log(_path(path), rr.LineStrips2D(strips, colors=colors))


# ---------- Graph (nodes/edges) ----------
def graph(
    origin: str,
    *,
    nodes: Sequence[str],
    labels: Optional[Sequence[str]] = None,
    colors: Optional[Sequence[Sequence[int]]] = None,  # RGBA
    radii: Optional[Sequence[float]] = None,
    edges: Sequence[Tuple[str, str]] = (),
    directed: bool = True,
) -> None:
    """
    Log a GraphNodes/GraphEdges pair at the given origin.
    Use together with a blueprint GraphView for force-layout in the viewer.
    """
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.log(_path(origin), rr.GraphNodes(nodes, labels=labels, colors=colors, radii=radii))
        if edges:
            graph_type_enum = getattr(rr, "GraphType", None)
            if graph_type_enum is not None:
                gt = graph_type_enum.Directed if directed else getattr(graph_type_enum, "Undirected", "undirected")
            else:
                gt = "directed" if directed else "undirected"
            rr.log(_path(origin), rr.GraphEdges(edges, graph_type=gt))


def send_blueprint(blueprint: Any, make_active: bool = True, make_default: bool = False) -> None:
    if not _backend:
        return
    _, rr = _backend
    with contextlib.suppress(Exception):
        rr.send_blueprint(blueprint, make_active=make_active, make_default=make_default)
