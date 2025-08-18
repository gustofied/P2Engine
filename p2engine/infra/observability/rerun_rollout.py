"""
Rerun visualizations for P2Engine rollouts.

Right pane (vertical):
  • Network graph (Spatial2D) – nodes = messages, edges = transitions (with timeline)
  • Team docs – ALL teams as tabbed panes (TextDocumentView, one per team)
  • Metrics (CLI) – mirrored rich table

Notes:
- Nodes are UNLABELED, colored by VARIANT, with larger default radii.
- We keep a fixed bounds frame so the aspect looks good.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple, List
import logging
import os
import math
import hashlib

from . import rerun_obs as rr

logger = logging.getLogger(__name__)

__all__ = [
    # Layout
    "send_default_blueprint",
    "send_rollout_blueprint",
    # Primary content
    "log_rollout_yaml",
    "log_rollout_config",
    # Team doc
    "log_team_stack_doc",
    # CLI mirror
    "log_cli_metrics",
    # Graph
    "log_graph_static",
    "log_graph_events",
    # Optional/extended
    "log_rollout_start",
    "log_variant_metrics",
    "log_pareto_point",
    "log_variant_config",
    "log_ledger_snapshot",
]

# -----------------------------------------------------------------------------
# Path helpers
# -----------------------------------------------------------------------------
def _rollout_path(rollout_id: str, team: Optional[str] = None, variant: Optional[str] = None) -> str:
    parts = [f"rollouts/{rollout_id}"]
    if team:
        parts.append(team)
    if variant:
        parts.append(variant)
    return "/".join(parts)

# -----------------------------------------------------------------------------
# Docs & YAML
# -----------------------------------------------------------------------------
def log_rollout_config(rollout_id: str, config: Dict[str, Any]) -> None:
    try:
        rr.json_doc(f"{_rollout_path(rollout_id)}/config", config)
    except Exception as e:
        logger.debug("log_rollout_config failed: %s", e)

def log_rollout_yaml(rollout_id: str, spec_path: str, yaml_text: str) -> None:
    try:
        name = os.path.basename(spec_path)
        md = f"# {name}\n\n```yaml\n{yaml_text}\n```"
        rr.text_doc(f"{_rollout_path(rollout_id)}/config/{name}", md, media_type="text/markdown")
    except Exception as e:
        logger.debug("log_rollout_yaml failed: %s", e)

def log_team_stack_doc(rollout_id: str, team_id: str, markdown_text: str) -> None:
    try:
        rr.text_doc(f"{_rollout_path(rollout_id)}/stacks/{team_id}", markdown_text, media_type="text/markdown")
    except Exception as e:
        logger.debug("log_team_stack_doc failed: %s", e)

def log_cli_metrics(rollout_id: str, metrics_block_text: str) -> None:
    try:
        md = "## Roll-out Metrics (per variant)\n\n```text\n" + metrics_block_text.rstrip() + "\n```\n"
        rr.text_doc(f"{_rollout_path(rollout_id)}/reports/metrics_cli", md, media_type="text/markdown")
    except Exception as e:
        logger.debug("log_cli_metrics failed: %s", e)

# -----------------------------------------------------------------------------
# Colors/sizing
# -----------------------------------------------------------------------------
def _stable_hue(name: str) -> float:
    h = int(hashlib.sha1(name.encode("utf-8")).hexdigest(), 16)
    return (h % 360) / 360.0

def _hsv_to_rgba(h: float, s: float, v: float, a: int = 255) -> list[int]:
    i = int(h * 6); f = h * 6 - i
    p = int(255 * v * (1 - s))
    q = int(255 * v * (1 - f * s))
    t = int(255 * v * (1 - (1 - f) * s))
    v = int(255 * v)
    i = i % 6
    if   i == 0: r,g,b = v,t,p
    elif i == 1: r,g,b = q,v,p
    elif i == 2: r,g,b = p,v,t
    elif i == 3: r,g,b = p,q,v
    elif i == 4: r,g,b = t,p,v
    else:        r,g,b = v,p,q
    return [r,g,b,a]

def _color_for_variant(variant: str) -> list[int]:
    return _hsv_to_rgba(_stable_hue(variant), 0.78, 0.95, 255)

# -----------------------------------------------------------------------------
# Graph logging
# -----------------------------------------------------------------------------
def log_graph_static(
    rollout_id: str,
    positions: List[Tuple[float, float]],
    node_meta: List[Dict[str, str]],   # [{team, variant, kind, latency?}, ...]
    edges: List[Tuple[int, int]],
) -> None:
    """
    Log the *static* graph (nodes + all edges) once.
    - Nodes: unlabeled, colored by VARIANT, radius scales with latency (if provided).
            Default radius is generous so points are visible.
    - Edges: thin, dim lines (variant-tinted).
    - Bounds: a square polyline to keep aspect stable.
    """
    try:
        base = f"{_rollout_path(rollout_id)}/graph"

        # radii by latency (fallback to larger base)
        radii: List[float] = []
        colors_nodes: List[List[int]] = []
        for meta in node_meta:
            variant = meta.get("variant", "?")
            lat = float(meta.get("latency", 0.0) or 0.0)
            # map latency (sec) → radius in [10..24]
            radius = 10.0 + min(14.0, max(0.0, lat * 10.0))
            radii.append(radius)
            colors_nodes.append(_color_for_variant(variant))

        rr.points2d(f"{base}/nodes", positions, radii=radii, colors=colors_nodes, labels=None)

        # edges as strips
        strips: List[List[List[float]]] = []
        colors_edges: List[List[int]] = []
        for i, j in edges:
            try:
                p1 = positions[i]; p2 = positions[j]
                strips.append([[float(p1[0]), float(p1[1])], [float(p2[0]), float(p2[1])]])
                variant = node_meta[i].get("variant", "?")
                r, g, b, _ = _color_for_variant(variant)
                colors_edges.append([r, g, b, 90])  # dim alpha for static edges
            except Exception:
                continue
        if strips:
            rr.line_strips2d(f"{base}/edges", strips, colors=colors_edges)

        # bounds square (keeps a pleasant aspect/fit)
        bounds = [[-1000.0, -1000.0], [1000.0, -1000.0], [1000.0, 1000.0], [-1000.0, 1000.0], [-1000.0, -1000.0]]
        rr.line_strips2d(f"{base}/bounds", [bounds])

    except Exception as e:
        logger.debug("log_graph_static failed: %s", e)


def log_graph_events(
    rollout_id: str,
    events: List[Dict[str, Any]],
    *,
    timeline: str = "step",
) -> None:
    """
    Log an animated 'playhead' over time:
      events: [{i, j, t, variant, p1:[x,y], p2:[x,y]}, ...]
    We draw a bright edge and a bright point at destination at time t.
    """
    try:
        base = f"{_rollout_path(rollout_id)}/graph"

        for ev in events:
            t = float(ev["t"])
            variant = str(ev.get("variant", "?"))

            rr.set_time_seconds(timeline, t)

            strips = [[ev["p1"], ev["p2"]]]
            r, g, b, _ = _color_for_variant(variant)
            rr.line_strips2d(f"{base}/playhead_edge", strips, colors=[[r, g, b, 230]])
            rr.points2d(f"{base}/playhead_node", [ev["p2"]], radii=[12.0], colors=[[r, g, b, 240]], labels=None)

    except Exception as e:
        logger.debug("log_graph_events failed: %s", e)

# -----------------------------------------------------------------------------
# Optional/extended metrics
# -----------------------------------------------------------------------------
def log_rollout_start(rollout_id: str, teams: int, total_variants: int, config: Dict[str, Any]) -> None:
    base = _rollout_path(rollout_id)
    try:
        rr.kv(f"{base}/meta", status="started", teams=teams, total_variants=total_variants, start_time=config.get("start_time"))
        rr.json_doc(f"{base}/config", config)
    except Exception as e:
        logger.debug("log_rollout_start failed: %s", e)

def log_variant_metrics(rollout_id: str, team_id: str, variant_id: str, **metrics: Any) -> None:
    base = _rollout_path(rollout_id, team_id, variant_id)
    try:
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                rr.scalar(f"{base}/metrics/{key}", float(value))
        rr.json_doc(f"{base}/metrics/snapshot", dict(metrics))
        rr.scalar(f"{_rollout_path(rollout_id)}/leaderboard/{team_id}_{variant_id}/score", float(metrics.get("score", 0.0)))
    except Exception as e:
        logger.debug("log_variant_metrics failed: %s", e)

def log_pareto_point(rollout_id: str, team_id: str, variant_id: str, *, score: float, cost: float, tokens: int) -> None:
    try:
        rr.json_doc(
            f"{_rollout_path(rollout_id)}/pareto/{team_id}_{variant_id}",
            {"team": team_id, "variant": variant_id, "score": float(score), "cost": float(cost), "tokens": int(tokens), "label": f"{team_id}/{variant_id}"},
        )
    except Exception as e:
        logger.debug("log_pareto_point failed: %s", e)

def log_variant_config(rollout_id: str, team_id: str, variant_id: str, config: Dict[str, Any]) -> None:
    try:
        rr.json_doc(f"{_rollout_path(rollout_id, team_id, variant_id)}/config", config)
    except Exception as e:
        logger.debug("log_variant_config failed: %s", e)

def log_ledger_snapshot(rollout_id: str, label: str, snapshot: Dict[str, Any]) -> None:
    try:
        base = f"{_rollout_path(rollout_id)}/ledger/{label}"
        rr.json_doc(f"{base}/snapshot", snapshot)
        metrics = snapshot.get("metrics", {}) or {}
        for key, value in metrics.items():
            if isinstance(value, (int, float)):
                rr.scalar(f"{base}/metrics/{key}", float(value))
        for wallet in snapshot.get("wallets", []) or []:
            agent_id = wallet.get("agent_id")
            balance = wallet.get("balance", 0.0)
            if agent_id:
                rr.scalar(f"{base}/agents/{agent_id}/balance", float(balance))
    except Exception as e:
        logger.debug("log_ledger_snapshot failed: %s", e)

# -----------------------------------------------------------------------------
# Blueprints (layouts)
# -----------------------------------------------------------------------------
def send_default_blueprint() -> None:
    try:
        import rerun.blueprint as rrb
    except Exception as e:
        logger.debug("Blueprint import failed; skipping default layout: %s", e)
        return

    try:
        bp = rrb.Blueprint(
            rrb.TextDocumentView(origin=rr.abs_path("rollouts/**/config/*"), name="Rollout Configs"),
            collapse_panels=True,
        )
        rr.send_blueprint(bp, make_active=False, make_default=True)
    except Exception as e:
        logger.debug("send_default_blueprint failed: %s", e)

def send_rollout_blueprint(
    rollout_id: str,
    spec_name: str,
    variants: Sequence[Tuple[str, str]],
    teams: Sequence[str],
    *,
    make_active: bool = True,
    make_default: bool = True,
) -> None:
    """
    Left  = TextDocumentView (YAML)
    Right = Vertical(
              Spatial2DView           -> /graph/**
              Tabs("Teams")           -> one TextDocumentView per /stacks/<team>
              TextDocumentView        -> /reports/metrics_cli
            )
    """
    try:
        import rerun.blueprint as rrb
    except Exception as e:
        logger.debug("Blueprint import failed; skipping rollout layout: %s", e)
        return

    try:
        # Left: YAML/spec
        left = rrb.TextDocumentView(
            origin=rr.abs_path(f"{_rollout_path(rollout_id)}/config/{spec_name}"),
            name="Rollout configuration",
        )

        # Graph view (goes first on the right)
        graph_view = rrb.Spatial2DView(
            origin=rr.abs_path(f"{_rollout_path(rollout_id)}/graph"),
            name="Network graph",
        )

        # Team docs: build one TextDocumentView per team and show as tabs.
        # If no teams provided, fall back to the overall stacks folder.
        if teams:
            team_views: List[Any] = [
                rrb.TextDocumentView(
                    origin=rr.abs_path(f"{_rollout_path(rollout_id)}/stacks/{team}"),
                    name=str(team),
                )
                for team in teams
            ]
            # Active tab defaults to the first team.
            teams_container = rrb.Tabs(*team_views, name="Teams", active_tab=str(teams[0]))
        else:
            teams_container = rrb.TextDocumentView(
                origin=rr.abs_path(f"{_rollout_path(rollout_id)}/stacks"),
                name="team",
            )

        # Metrics (CLI) last on the right
        metrics_doc = rrb.TextDocumentView(
            origin=rr.abs_path(f"{_rollout_path(rollout_id)}/reports/metrics_cli"),
            name="Metrics (CLI)",
        )

        # Assemble: Right = Vertical(Graph → Teams Tabs → Metrics)
        right = rrb.Vertical(graph_view, teams_container, metrics_doc)

        # Final blueprint: Horizontal(Left YAML, Right)
        bp = rrb.Blueprint(rrb.Horizontal(left, right), collapse_panels=True)

        rr.send_blueprint(bp, make_active=make_active, make_default=make_default)
    except Exception as e:
        logger.debug("send_rollout_blueprint failed: %s", e)
