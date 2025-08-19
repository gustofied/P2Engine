"""
Enhanced Rerun visualizations for P2Engine rollouts.

World graph improvements:
- Force-directed layout for clean, organic structure (computed here, not in viewer)
- Node size represents activity level
- Edges show delegations and tool calls (different strengths)
- Colors represent teams/variants
- Animated flow shows current activity
- Aspect ratio aware canvas; stays readable regardless of window size
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple, List
import logging
import os
import math
import hashlib
import re
import random
from collections import defaultdict
from dataclasses import dataclass

from . import rerun_obs as rr

logger = logging.getLogger(__name__)

__all__ = [
    "send_default_blueprint",
    "send_rollout_blueprint",
    "log_rollout_yaml",
    "log_rollout_config",
    "log_team_stack_doc",
    "log_stack_line",
    "log_cli_metrics",
    "log_graph_static",
    "log_graph_events",
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
# Coloring utilities
# -----------------------------------------------------------------------------

def _stable_hue(name: str) -> float:
    h = int(hashlib.sha1(name.encode("utf-8")).hexdigest(), 16)
    return (h % 360) / 360.0

def _hsv_to_rgba(h: float, s: float, v: float, a: int = 255) -> list[int]:
    i = int(h * 6)
    f = h * 6 - i
    p = int(255 * v * (1 - s))
    q = int(255 * v * (1 - f * s))
    t = int(255 * v * (1 - (1 - f) * s))
    v = int(255 * v)
    i = i % 6
    if i == 0:
        r, g, b = v, t, p
    elif i == 1:
        r, g, b = q, v, p
    elif i == 2:
        r, g, b = p, v, t
    elif i == 3:
        r, g, b = p, q, v
    elif i == 4:
        r, g, b = t, p, v
    else:
        r, g, b = v, p, q
    return [r, g, b, a]

def _color_for_variant(variant: str) -> list[int]:
    return _hsv_to_rgba(_stable_hue(variant), 0.78, 0.95, 255)

def _color_for_team(team: str) -> list[int]:
    """Generate consistent color for a team."""
    return _hsv_to_rgba(_stable_hue(team), 0.65, 0.85, 255)

# -----------------------------------------------------------------------------
# Enhanced Graph Data Structures
# -----------------------------------------------------------------------------

@dataclass
class GraphNode:
    """Represents a node in the world graph."""
    id: str
    type: str  # 'agent', 'tool', 'state'
    label: str
    position: Tuple[float, float]
    size: float = 10.0
    color: List[int] | None = None
    activity_count: float = 0.0
    team: str | None = None

@dataclass 
class GraphEdge:
    """Represents an edge in the world graph."""
    source: str
    target: str
    type: str  # 'delegation', 'tool_call', 'transition'
    weight: float = 1.0
    color: List[int] | None = None

# -----------------------------------------------------------------------------
# Force-directed layout (Fruchterman–Reingold style)
# -----------------------------------------------------------------------------

class _ForceLayout:
    """
    Simple force-based layout that keeps a nice aspect ratio and is deterministic.
    """
    def __init__(self, width: float, height: float, seed: int = 42):
        self.W = width
        self.H = height
        self.cx = 0.0
        self.cy = 0.0
        random.seed(seed)

    def run(
        self,
        node_ids: List[str],
        pos: Dict[str, Tuple[float, float]],
        edges: List[Tuple[str, str]],
        edge_strength: Dict[Tuple[str, str], float],
        iterations: int = 30,
    ) -> None:
        n = max(1, len(node_ids))
        area = self.W * self.H
        k = math.sqrt(area / n)
        # Cooling schedule
        t0 = max(self.W, self.H) * 0.12
        gravity = 0.02  # gentle pull to center
        # Precompute edge list (u, v, weight)
        e_list = [(u, v, max(0.2, edge_strength.get((u, v), 1.0))) for (u, v) in edges]

        for it in range(iterations):
            t = t0 * (1.0 - it / max(1, iterations))
            disp: Dict[str, List[float]] = {nid: [0.0, 0.0] for nid in node_ids}

            # Repulsion (O(n^2) – fine for ~few hundred nodes)
            for i in range(n):
                u = node_ids[i]
                ux, uy = pos[u]
                for j in range(i + 1, n):
                    v = node_ids[j]
                    vx, vy = pos[v]
                    dx = ux - vx
                    dy = uy - vy
                    dist = math.hypot(dx, dy) or 1e-6
                    # Fruchterman repulsive force ~ k^2 / d
                    f = (k * k) / dist
                    rx = (dx / dist) * f
                    ry = (dy / dist) * f
                    disp[u][0] += rx; disp[u][1] += ry
                    disp[v][0] -= rx; disp[v][1] -= ry

            # Attraction along edges
            for u, v, w in e_list:
                ux, uy = pos[u]
                vx, vy = pos[v]
                dx = ux - vx
                dy = uy - vy
                dist = math.hypot(dx, dy) or 1e-6
                # Fruchterman attractive force ~ d^2 / k
                f = (dist * dist) / k
                f *= w  # strengthen delegations etc.
                ax = (dx / dist) * f
                ay = (dy / dist) * f
                disp[u][0] -= ax; disp[u][1] -= ay
                disp[v][0] += ax; disp[v][1] += ay

            # Gravity to center + move with temperature cap
            for nid in node_ids:
                dx, dy = disp[nid]
                # gentle gravity
                px, py = pos[nid]
                dx += (self.cx - px) * gravity
                dy += (self.cy - py) * gravity

                mag = math.hypot(dx, dy) or 1e-6
                limit = t / mag
                px += dx * min(1.0, limit)
                py += dy * min(1.0, limit)

                # clamp to canvas
                halfW, halfH = self.W * 0.5, self.H * 0.5
                px = max(-halfW, min(halfW, px))
                py = max(-halfH, min(halfH, py))
                pos[nid] = (px, py)

# -----------------------------------------------------------------------------
# Graph builder
# -----------------------------------------------------------------------------

class WorldGraphBuilder:
    """Builds & lays out the world graph from rollout data."""
    
    def __init__(self, rollout_id: str):
        self.rollout_id = rollout_id
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        # Cached positions (persist across updates)
        self.positions: Dict[str, Tuple[float, float]] = {}
        # Track activity
        self.agent_activity: Dict[str, float] = defaultdict(float)
        self.tool_usage: Dict[str, float] = defaultdict(float)
        self.delegations: List[Tuple[str, str, str]] = []  # (from, to, variant)
        self.agent_teams: Dict[str, str] = {}

        # Canvas / aspect
        self.W = float(os.getenv("WORLD_GRAPH_WIDTH", "1200"))
        self.H = float(os.getenv("WORLD_GRAPH_HEIGHT", "750"))
        self.layout = _ForceLayout(self.W, self.H, seed=17)
        
    def _ensure_pos(self, node_id: str) -> Tuple[float, float]:
        if node_id not in self.positions:
            # random but bounded initial positions (gives nicer settle)
            halfW, halfH = self.W * 0.45, self.H * 0.45
            self.positions[node_id] = (random.uniform(-halfW, halfW), random.uniform(-halfH, halfH))
        return self.positions[node_id]

    def add_agent_node(self, agent_id: str, team: str | None = None, variant: str | None = None):
        if agent_id not in self.nodes:
            color = _color_for_team(team) if team else (_color_for_variant(variant) if variant else [100, 100, 200, 255])
            self._ensure_pos(agent_id)
            self.nodes[agent_id] = GraphNode(
                id=agent_id,
                type='agent',
                label=agent_id.replace('_', ' ').title(),
                position=self.positions[agent_id],
                size=15.0,
                color=color,
                team=team
            )
    
    def add_tool_node(self, tool_name: str):
        if tool_name not in self.nodes:
            tool_colors = {
                'delegate': [255, 100, 100, 220],
                'transfer_funds': [100, 255, 100, 220],
                'check_balance': [100, 200, 255, 220],
                'transaction_history': [100, 200, 255, 220],
                'reward_agent': [255, 200, 100, 220],
                'get_weather': [200, 200, 100, 220],
            }
            color = tool_colors.get(tool_name, [160, 160, 160, 220])
            self._ensure_pos(tool_name)
            self.nodes[tool_name] = GraphNode(
                id=tool_name,
                type='tool',
                label=tool_name.replace('_', ' ').title(),
                position=self.positions[tool_name],
                size=8.0,
                color=color
            )
    
    def add_delegation(self, src: str, dst: str, team: str | None = None, variant: str | None = None):
        self.add_agent_node(src, team=team, variant=variant)
        self.add_agent_node(dst)
        color = _color_for_variant(variant) if variant else [100, 100, 200, 150]
        self.edges.append(GraphEdge(source=src, target=dst, type='delegation', weight=1.6, color=color))
        self.agent_activity[src] += 1.0
        self.agent_activity[dst] += 1.0
        self.delegations.append((src, dst, variant or ""))

    def add_tool_call(self, agent_id: str, tool_name: str, team: str | None = None, variant: str | None = None):
        self.add_agent_node(agent_id, team=team, variant=variant)
        self.add_tool_node(tool_name)
        color = _color_for_variant(variant) if variant else [100, 200, 100, 150]
        self.edges.append(GraphEdge(source=agent_id, target=tool_name, type='tool_call', weight=1.0, color=color))
        self.agent_activity[agent_id] += 1.0
        self.tool_usage[tool_name] += 1.0
        
    def update_node_sizes(self) -> None:
        max_activity = max(self.agent_activity.values()) if self.agent_activity else 1.0
        max_usage = max(self.tool_usage.values()) if self.tool_usage else 1.0
        for aid, c in self.agent_activity.items():
            if aid in self.nodes:
                self.nodes[aid].size = 10.0 + (22.0 * c / max_activity)
                self.nodes[aid].activity_count = c
        for tool, c in self.tool_usage.items():
            if tool in self.nodes:
                self.nodes[tool].size = 7.0 + (10.0 * c / max_usage)
                self.nodes[tool].activity_count = c

    def _force_relayout(self, iterations: int = 22) -> None:
        # Stable order: agents first, then tools by id
        node_ids = sorted(self.nodes.keys(), key=lambda nid: (self.nodes[nid].type, nid))
        # Ensure all have a starting pos & sync with .position
        for nid in node_ids:
            self._ensure_pos(nid)

        # Build edge list & strengths
        pair_edges: List[Tuple[str, str]] = []
        strengths: Dict[Tuple[str, str], float] = {}
        for e in self.edges:
            pair_edges.append((e.source, e.target))
            strengths[(e.source, e.target)] = e.weight

        # Run layout on our shared positions map
        self.layout.run(node_ids, self.positions, pair_edges, strengths, iterations=iterations)

        # Push back into nodes
        for nid in node_ids:
            self.nodes[nid].position = self.positions[nid]

    def to_rerun_format(self) -> Tuple[List[Tuple[float, float]], List[Dict], List[Tuple[int, int]]]:
        # Refresh visuals
        self.update_node_sizes()
        # Do a few iterations each update for smooth convergence
        self._force_relayout(iterations=14)

        # Stable order
        node_ids = sorted(self.nodes.keys(), key=lambda nid: (self.nodes[nid].type, nid))
        idx = {nid: i for i, nid in enumerate(node_ids)}

        positions: List[Tuple[float, float]] = [self.nodes[nid].position for nid in node_ids]
        node_meta: List[Dict[str, str]] = []
        for nid in node_ids:
            n = self.nodes[nid]
            meta = {
                "team": n.team or "world",
                "variant": nid,
                "kind": n.type,
                "label": n.label,
                "latency": f"{n.size/10.0:.3f}",
                "activity": f"{n.activity_count:.3f}",
                "color_r": str(n.color[0] if n.color else 100),
                "color_g": str(n.color[1] if n.color else 100),
                "color_b": str(n.color[2] if n.color else 200),
            }
            node_meta.append(meta)

        edges_idx: List[Tuple[int, int]] = []
        for e in self.edges:
            if e.source in idx and e.target in idx:
                edges_idx.append((idx[e.source], idx[e.target]))

        return positions, node_meta, edges_idx

# Global graph builder instance
_graph_builder: Optional[WorldGraphBuilder] = None

def get_graph_builder(rollout_id: str) -> WorldGraphBuilder:
    global _graph_builder
    if _graph_builder is None or _graph_builder.rollout_id != rollout_id:
        _graph_builder = WorldGraphBuilder(rollout_id)
    return _graph_builder

# -----------------------------------------------------------------------------
# Generic docs & logs
# -----------------------------------------------------------------------------

def log_rollout_config(rollout_id: str, config: Dict[str, Any]) -> None:
    try:
        rr.json_doc(f"{_rollout_path(rollout_id)}/config", config, timeless=True)
    except Exception as e:
        logger.debug("log_rollout_config failed: %s", e)

def log_rollout_yaml(rollout_id: str, spec_path: str, yaml_text: str) -> None:
    try:
        name = os.path.basename(spec_path)
        md = f"# {name}\n\n```yaml\n{yaml_text}\n```"
        rr.text_doc(f"{_rollout_path(rollout_id)}/config/{name}", md, media_type="text/markdown", timeless=True)
    except Exception as e:
        logger.debug("log_rollout_yaml failed: %s", e)

def log_team_stack_doc(rollout_id: str, team_id: str, markdown_text: str) -> None:
    try:
        rr.text_doc(
            f"{_rollout_path(rollout_id)}/stacks/{team_id}/summary",
            markdown_text,
            media_type="text/markdown",
            timeless=True,
        )
    except Exception as e:
        logger.debug("log_team_stack_doc failed: %s", e)

def log_stack_line(
    rollout_id: str,
    team_id: str,
    variant_id: str,
    *,
    idx: int,
    kind: str,
    content: str,
    t_step: Optional[float] = None,
) -> None:
    try:
        if t_step is not None:
            rr.set_time_seconds("step", t_step)

        path = f"{_rollout_path(rollout_id)}/stacks/{team_id}/{variant_id}"
        snippet = content if len(content) <= 500 else (content[:497] + "…")
        rr.text_log(f"{path}/log", f"[{variant_id}][{idx:03d}] {kind:<12} {snippet}")
        _update_graph_from_stack_line(rollout_id, team_id, variant_id, kind, content)
    except Exception as e:
        logger.debug("log_stack_line failed: %s", e)

def _update_graph_from_stack_line(
    rollout_id: str,
    team_id: str,
    variant_id: str,
    kind: str,
    content: str
) -> None:
    try:
        builder = get_graph_builder(rollout_id)
        agent_id = _infer_agent_from_variant(team_id, variant_id)

        if kind == "ToolCall":
            if '(' in content:
                tool_name = content.split('(')[0].strip()
                if agent_id:
                    builder.add_tool_call(agent_id, tool_name, team=team_id, variant=variant_id)
                if tool_name == 'delegate' and '{' in content:
                    try:
                        m = re.search(r"'agent_id':\s*'([^']+)'", content) or re.search(r'"agent_id":\s*"([^"]+)"', content)
                        if m and agent_id:
                            builder.add_delegation(agent_id, m.group(1), team=team_id, variant=variant_id)
                    except Exception:
                        pass

        elif kind == "AgentCall":
            if agent_id:
                m = re.search(r"agent[_\w]*", content.lower())
                if m:
                    target = m.group(0)
                    if target != agent_id:
                        builder.add_delegation(agent_id, target, team=team_id, variant=variant_id)

        elif kind == "ToolResult" and agent_id:
            builder.agent_activity[agent_id] += 0.5

        # Re-render static graph snapshot with fresh layout
        if builder.agent_activity or builder.tool_usage:
            positions, node_meta, edges = builder.to_rerun_format()
            if positions:
                _log_graph_static_enhanced(rollout_id, positions, node_meta, edges)

    except Exception as e:
        logger.debug("_update_graph_from_stack_line failed: %s", e)

def _infer_agent_from_variant(team_id: str, variant_id: str) -> Optional[str]:
    agent_map = {
        'joke_team': 'agent_alpha',
        'pun_team': 'agent_alpha',
        'problem_solvers': 'agent_alpha',
        'weather_service': 'agent_helper',
        'payment_coordinator': 'agent_alpha',
        'management_team': 'agent_alpha',
        'reward_distributor': 'treasurer',
    }
    v = variant_id.lower()
    if 'alpha' in v: return 'agent_alpha'
    if 'beta' in v: return 'agent_beta'
    if 'treasurer' in v: return 'treasurer'
    if 'helper' in v: return 'agent_helper'
    return agent_map.get(team_id)

def log_cli_metrics(rollout_id: str, metrics_block_text: str) -> None:
    try:
        md = "## Roll-out Metrics (per variant)\n\n```text\n" + metrics_block_text.rstrip() + "\n```\n"
        rr.text_doc(f"{_rollout_path(rollout_id)}/reports/metrics_cli", md, media_type="text/markdown", timeless=True)
    except Exception as e:
        logger.debug("log_cli_metrics failed: %s", e)

# -----------------------------------------------------------------------------
# Static graph logging (using Points2D/LineStrips2D)
# -----------------------------------------------------------------------------

def _log_graph_static_enhanced(
    rollout_id: str,
    positions: List[Tuple[float, float]],
    node_meta: List[Dict[str, str]],
    edges: List[Tuple[int, int]],
) -> None:
    try:
        base = f"{_rollout_path(rollout_id)}/graph"
        radii: List[float] = []
        colors_nodes: List[List[int]] = []
        labels: List[str] = []

        for meta in node_meta:
            k = meta.get("kind", "state")
            if k == "agent":
                radius = float(meta.get("latency", 1.0)) * 15.0
                color = [
                    int(meta.get("color_r", 100)),
                    int(meta.get("color_g", 100)),
                    int(meta.get("color_b", 200)),
                    255,
                ]
                label = meta.get("label", meta.get("variant", ""))
            elif k == "tool":
                radius = float(meta.get("latency", 1.0)) * 10.0
                color = [
                    int(meta.get("color_r", 150)),
                    int(meta.get("color_g", 150)),
                    int(meta.get("color_b", 150)),
                    210,
                ]
                label = meta.get("label", meta.get("variant", ""))
            else:
                variant = meta.get("variant", "?")
                radius = float(meta.get("latency", 1.0)) * 10.0
                color = _color_for_variant(variant)
                label = meta.get("label", "")

            radii.append(radius)
            colors_nodes.append(color)
            labels.append(label)

        # Nodes
        rr.points2d(f"{base}/nodes", positions, radii=radii, colors=colors_nodes, labels=labels if any(labels) else None, timeless=True)

        # Edges
        if edges:
            strips: List[List[List[float]]] = []
            colors_edges: List[List[int]] = []
            for (i, j) in edges:
                try:
                    p1 = positions[i]; p2 = positions[j]
                    strips.append([[float(p1[0]), float(p1[1])], [float(p2[0]), float(p2[1])]])
                    # Color edge by source node tint, semi-transparent
                    c = colors_nodes[i]
                    colors_edges.append([c[0], c[1], c[2], 140])
                except Exception:
                    continue
            if strips:
                rr.line_strips2d(f"{base}/edges", strips, colors=colors_edges, timeless=True)

        # Bounds rectangle
        halfW = float(os.getenv("WORLD_GRAPH_WIDTH", "1200")) * 0.5
        halfH = float(os.getenv("WORLD_GRAPH_HEIGHT", "750")) * 0.5
        bounds = [[-halfW, -halfH], [halfW, -halfH], [halfW, halfH], [-halfW, halfH], [-halfW, -halfH]]
        rr.line_strips2d(f"{base}/bounds", [bounds], colors=[[180,180,180,60]], timeless=True)

    except Exception as e:
        logger.debug("_log_graph_static_enhanced failed: %s", e)

def log_graph_static(
    rollout_id: str,
    positions: List[Tuple[float, float]],
    node_meta: List[Dict[str, str]],
    edges: List[Tuple[int, int]],
) -> None:
    _log_graph_static_enhanced(rollout_id, positions, node_meta, edges)

def log_graph_events(
    rollout_id: str,
    events: List[Dict[str, Any]],
    *,
    timeline: str = "step",
) -> None:
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
# Rollout-level logging (unchanged)
# -----------------------------------------------------------------------------

def log_rollout_start(rollout_id: str, teams: int, total_variants: int, config: Dict[str, Any]) -> None:
    base = _rollout_path(rollout_id)
    try:
        rr.kv(f"{base}/meta", timeless=True, status="started", teams=int(teams), total_variants=int(total_variants), start_time=config.get("start_time"))
        rr.json_doc(f"{base}/config", config, timeless=True)
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
        rr.json_doc(f"{_rollout_path(rollout_id)}/pareto/{team_id}_{variant_id}", {"team": team_id, "variant": variant_id, "score": float(score), "cost": float(cost), "tokens": int(tokens), "label": f"{team_id}/{variant_id}"})
    except Exception as e:
        logger.debug("log_pareto_point failed: %s", e)

def log_variant_config(rollout_id: str, team_id: str, variant_id: str, config: Dict[str, Any]) -> None:
    try:
        rr.json_doc(f"{_rollout_path(rollout_id, team_id, variant_id)}/config", config, timeless=True)
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
# Blueprints
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
              Spatial2DView           -> /graph/**  (WORLD graph: force-layouted Points2D)
              TextLogView (all teams) -> /stacks/**
              TextDocumentView        -> /reports/metrics_cli
            )
    """
    try:
        import rerun.blueprint as rrb
    except Exception as e:
        logger.debug("Blueprint import failed; skipping rollout layout: %s", e)
        return

    try:
        left = rrb.TextDocumentView(
            origin=rr.abs_path(f"{_rollout_path(rollout_id)}/config/{spec_name}"),
            name="Rollout configuration",
        )

        graph_view = rrb.Spatial2DView(
            origin=rr.abs_path(f"{_rollout_path(rollout_id)}/graph"),
            name="World graph",
        )

        TextLogView = getattr(rrb, "TextLogView", None)
        TeamPaneView = TextLogView or rrb.TextDocumentView

        teams_container = TeamPaneView(
            origin=rr.abs_path(f"{_rollout_path(rollout_id)}/stacks"),
            name="Team logs",
        )

        metrics_doc = rrb.TextDocumentView(
            origin=rr.abs_path(f"{_rollout_path(rollout_id)}/reports/metrics_cli"),
            name="Metrics (CLI)",
        )

        # Short description next to the graph (helps new users)
        try:
            desc = (
                "# World Graph\n"
                "- **Position**: computed via force layout\n"
                "- **Color**: team/variant grouping\n"
                "- **Size**: recent activity\n"
                "- **Edges**: delegations (strong) & tool calls\n"
            )
            rr.text_doc(f"{_rollout_path(rollout_id)}/graph/description", desc, media_type="text/markdown", timeless=True)
        except Exception:
            pass

        right = rrb.Vertical(graph_view, teams_container, metrics_doc)
        bp = rrb.Blueprint(rrb.Horizontal(left, right), collapse_panels=True)

        rr.send_blueprint(bp, make_active=make_active, make_default=make_default)
        try:
            rr.set_time_seconds("step", 0.0)
        except Exception:
            pass

    except Exception as e:
        logger.debug("send_rollout_blueprint failed: %s", e)
