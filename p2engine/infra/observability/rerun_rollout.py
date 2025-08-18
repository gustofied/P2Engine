"""
Enhanced Rerun visualizations for P2Engine rollouts.

World graph improvements:
- Shows agent interactions as a network
- Node size represents activity level
- Edges show delegations and tool calls
- Colors represent teams/variants
- Animated flow shows current activity
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Sequence, Tuple, List
import logging
import os
import math
import hashlib
import re
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
    color: List[int] = None
    activity_count: int = 0
    team: str = None
    
@dataclass 
class GraphEdge:
    """Represents an edge in the world graph."""
    source: str
    target: str
    type: str  # 'delegation', 'tool_call', 'transition'
    weight: int = 1
    color: List[int] = None

class WorldGraphBuilder:
    """Builds a comprehensive world graph from rollout data."""
    
    def __init__(self, rollout_id: str):
        self.rollout_id = rollout_id
        self.nodes: Dict[str, GraphNode] = {}
        self.edges: List[GraphEdge] = []
        self.agent_positions: Dict[str, Tuple[float, float]] = {}
        self.tool_positions: Dict[str, Tuple[float, float]] = {}
        
        # Track activity
        self.agent_activity: Dict[str, int] = defaultdict(int)
        self.tool_usage: Dict[str, int] = defaultdict(int)
        self.delegations: List[Tuple[str, str, str]] = []  # (from_agent, to_agent, variant)
        
        # Track teams
        self.agent_teams: Dict[str, str] = {}
        
    def add_agent_node(self, agent_id: str, team: str = None, variant: str = None):
        """Add an agent node to the graph."""
        if agent_id not in self.nodes:
            # Position agents in a circle
            pos = self._get_agent_position(agent_id)
            
            # Color by team if available, otherwise by variant
            if team:
                color = _color_for_team(team)
                self.agent_teams[agent_id] = team
            elif variant:
                color = _color_for_variant(variant)
            else:
                color = [100, 100, 200, 255]
            
            self.nodes[agent_id] = GraphNode(
                id=agent_id,
                type='agent',
                label=agent_id.replace('_', ' ').title(),
                position=pos,
                size=15.0,
                color=color,
                team=team
            )
    
    def add_tool_node(self, tool_name: str):
        """Add a tool node to the graph."""
        if tool_name not in self.nodes:
            # Position tools in inner circle
            pos = self._get_tool_position(tool_name)
            
            # Different colors for different tool types
            tool_colors = {
                'delegate': [255, 100, 100, 200],  # Red for delegation
                'transfer_funds': [100, 255, 100, 200],  # Green for money
                'check_balance': [100, 200, 255, 200],  # Blue for info
                'transaction_history': [100, 200, 255, 200],
                'reward_agent': [255, 200, 100, 200],  # Orange for rewards
                'get_weather': [200, 200, 100, 200],  # Yellow for data
            }
            
            color = tool_colors.get(tool_name, [150, 150, 150, 200])
            
            self.nodes[tool_name] = GraphNode(
                id=tool_name,
                type='tool',
                label=tool_name.replace('_', ' ').title(),
                position=pos,
                size=8.0,
                color=color
            )
    
    def add_delegation(self, from_agent: str, to_agent: str, team: str = None, variant: str = None):
        """Add a delegation edge between agents."""
        self.add_agent_node(from_agent, team=team, variant=variant)
        self.add_agent_node(to_agent)
        
        color = _color_for_variant(variant) if variant else [100, 100, 200, 150]
        self.edges.append(GraphEdge(
            source=from_agent,
            target=to_agent,
            type='delegation',
            color=color
        ))
        
        self.agent_activity[from_agent] += 1
        self.agent_activity[to_agent] += 1
        self.delegations.append((from_agent, to_agent, variant))
        
    def add_tool_call(self, agent_id: str, tool_name: str, team: str = None, variant: str = None):
        """Add a tool call edge from agent to tool."""
        self.add_agent_node(agent_id, team=team, variant=variant)
        self.add_tool_node(tool_name)
        
        color = _color_for_variant(variant) if variant else [100, 200, 100, 150]
        self.edges.append(GraphEdge(
            source=agent_id,
            target=tool_name,
            type='tool_call',
            color=color
        ))
        
        self.agent_activity[agent_id] += 1
        self.tool_usage[tool_name] += 1
        
    def _get_agent_position(self, agent_id: str) -> Tuple[float, float]:
        """Calculate position for an agent node."""
        if agent_id not in self.agent_positions:
            # Main agents in outer circle
            agent_list = ['agent_alpha', 'agent_beta', 'treasurer', 'agent_helper', 'child', 'agent_lemy']
            
            # Position known agents in specific spots
            if agent_id in agent_list:
                idx = agent_list.index(agent_id)
                total = len(agent_list)
            else:
                # Unknown agents go in between
                idx = len(self.agent_positions)
                total = max(8, len(self.agent_positions) + 1)
            
            angle = (2 * math.pi * idx) / total - math.pi / 2  # Start from top
            radius = 300
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            self.agent_positions[agent_id] = (x, y)
            
        return self.agent_positions[agent_id]
    
    def _get_tool_position(self, tool_name: str) -> Tuple[float, float]:
        """Calculate position for a tool node."""
        if tool_name not in self.tool_positions:
            # Tools in inner circle
            tool_list = ['get_weather', 'delegate', 'check_balance', 'transfer_funds', 
                        'transaction_history', 'reward_agent']
            
            if tool_name in tool_list:
                idx = tool_list.index(tool_name)
                total = len(tool_list)
            else:
                idx = len(self.tool_positions)
                total = max(6, len(self.tool_positions) + 1)
                
            angle = (2 * math.pi * idx) / total - math.pi / 2
            radius = 150
            x = radius * math.cos(angle)
            y = radius * math.sin(angle)
            self.tool_positions[tool_name] = (x, y)
            
        return self.tool_positions[tool_name]
    
    def update_node_sizes(self):
        """Update node sizes based on activity."""
        max_activity = max(self.agent_activity.values()) if self.agent_activity else 1
        max_usage = max(self.tool_usage.values()) if self.tool_usage else 1
        
        for agent_id, count in self.agent_activity.items():
            if agent_id in self.nodes:
                # Size between 10 and 30 based on activity
                self.nodes[agent_id].size = 10 + (20 * count / max_activity)
                self.nodes[agent_id].activity_count = count
                
        for tool_name, count in self.tool_usage.items():
            if tool_name in self.nodes:
                # Size between 5 and 15 based on usage
                self.nodes[tool_name].size = 5 + (10 * count / max_usage)
                self.nodes[tool_name].activity_count = count
    
    def to_rerun_format(self) -> Tuple[List[Tuple[float, float]], List[Dict], List[Tuple[int, int]]]:
        """Convert to format expected by log_graph_static."""
        self.update_node_sizes()
        
        # Sort nodes by type then name for consistent indexing
        node_ids = sorted(self.nodes.keys(), key=lambda x: (self.nodes[x].type, x))
        node_idx = {nid: i for i, nid in enumerate(node_ids)}
        
        positions = []
        node_meta = []
        
        for nid in node_ids:
            node = self.nodes[nid]
            positions.append(node.position)
            
            # Meta includes type info for better visualization
            meta = {
                "team": node.team or "world",
                "variant": nid,
                "kind": node.type,
                "label": node.label,
                "latency": str(node.size / 10.0),  # Normalized for radius scaling
                "activity": str(node.activity_count),
                "color_r": str(node.color[0]) if node.color else "100",
                "color_g": str(node.color[1]) if node.color else "100",
                "color_b": str(node.color[2]) if node.color else "200",
            }
            node_meta.append(meta)
        
        # Convert edges to index pairs
        edges = []
        for edge in self.edges:
            if edge.source in node_idx and edge.target in node_idx:
                edges.append((node_idx[edge.source], node_idx[edge.target]))
                
        return positions, node_meta, edges

# Global graph builder instance
_graph_builder: Optional[WorldGraphBuilder] = None

def get_graph_builder(rollout_id: str) -> WorldGraphBuilder:
    """Get or create the global graph builder."""
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
    """
    Stream a single stack line and update world graph.
    """
    try:
        if t_step is not None:
            rr.set_time_seconds("step", t_step)

        path = f"{_rollout_path(rollout_id)}/stacks/{team_id}/{variant_id}"
        snippet = content if len(content) <= 500 else (content[:497] + "…")
        rr.text_log(f"{path}/log", f"[{variant_id}][{idx:03d}] {kind:<12} {snippet}")
        
        # Update world graph based on this interaction
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
    """Update world graph based on stack line content."""
    try:
        builder = get_graph_builder(rollout_id)
        
        # Infer the agent from team/variant
        agent_id = _infer_agent_from_variant(team_id, variant_id)
        
        # Parse different kinds of interactions
        if kind == "ToolCall":
            # Extract tool name from content like "delegate({'agent_id': 'agent_helper', ...})"
            if '(' in content:
                tool_name = content.split('(')[0].strip()
                
                if agent_id:
                    builder.add_tool_call(agent_id, tool_name, team=team_id, variant=variant_id)
                
                # Special handling for delegate tool
                if tool_name == 'delegate' and '{' in content:
                    try:
                        # Extract target agent from delegate call
                        match = re.search(r"'agent_id':\s*'([^']+)'", content)
                        if not match:
                            match = re.search(r'"agent_id":\s*"([^"]+)"', content)
                        
                        if match and agent_id:
                            target_agent = match.group(1)
                            builder.add_delegation(agent_id, target_agent, team=team_id, variant=variant_id)
                    except:
                        pass
                        
        elif kind == "AgentCall":
            # Direct agent-to-agent call
            if agent_id:
                # Try to extract target agent
                match = re.search(r"agent[_\w]*", content.lower())
                if match:
                    target = match.group(0)
                    if target != agent_id:
                        builder.add_delegation(agent_id, target, team=team_id, variant=variant_id)
        
        elif kind == "ToolResult":
            # Track tool results to show activity
            if agent_id:
                builder.agent_activity[agent_id] += 0.5  # Half weight for results
        
        # Periodically update the graph visualization
        if builder.agent_activity or builder.tool_usage:
            positions, node_meta, edges = builder.to_rerun_format()
            if positions:
                _log_graph_static_enhanced(rollout_id, positions, node_meta, edges)
            
    except Exception as e:
        logger.debug("_update_graph_from_stack_line failed: %s", e)

def _infer_agent_from_variant(team_id: str, variant_id: str) -> Optional[str]:
    """Infer agent ID from team and variant info."""
    # Common patterns in rollouts
    agent_map = {
        'joke_team': 'agent_alpha',
        'pun_team': 'agent_alpha',
        'problem_solvers': 'agent_alpha',
        'weather_service': 'agent_helper',
        'payment_coordinator': 'agent_alpha',
        'management_team': 'agent_alpha',
        'reward_distributor': 'treasurer',
    }
    
    # Check if variant contains agent info
    if 'alpha' in variant_id.lower():
        return 'agent_alpha'
    elif 'beta' in variant_id.lower():
        return 'agent_beta'
    elif 'treasurer' in variant_id.lower():
        return 'treasurer'
    elif 'helper' in variant_id.lower():
        return 'agent_helper'
    
    return agent_map.get(team_id)

def log_cli_metrics(rollout_id: str, metrics_block_text: str) -> None:
    try:
        md = "## Roll-out Metrics (per variant)\n\n```text\n" + metrics_block_text.rstrip() + "\n```\n"
        rr.text_doc(f"{_rollout_path(rollout_id)}/reports/metrics_cli", md, media_type="text/markdown", timeless=True)
    except Exception as e:
        logger.debug("log_cli_metrics failed: %s", e)

# -----------------------------------------------------------------------------
# Enhanced Graph logging
# -----------------------------------------------------------------------------

def _log_graph_static_enhanced(
    rollout_id: str,
    positions: List[Tuple[float, float]],
    node_meta: List[Dict[str, str]],
    edges: List[Tuple[int, int]],
) -> None:
    """Enhanced static graph with better visuals."""
    try:
        base = f"{_rollout_path(rollout_id)}/graph"
        
        radii: List[float] = []
        colors_nodes: List[List[int]] = []
        labels: List[str] = []
        
        for meta in node_meta:
            # Different visuals for different node types
            node_type = meta.get("kind", "state")
            
            if node_type == "agent":
                # Agents get team/variant colors and larger size
                radius = float(meta.get("latency", 1.0)) * 15
                color = [
                    int(meta.get("color_r", 100)),
                    int(meta.get("color_g", 100)),
                    int(meta.get("color_b", 200)),
                    255
                ]
                label = meta.get("label", meta.get("variant", ""))
                
            elif node_type == "tool":
                # Tools get their specific colors and medium size
                radius = float(meta.get("latency", 1.0)) * 10
                color = [
                    int(meta.get("color_r", 150)),
                    int(meta.get("color_g", 150)),
                    int(meta.get("color_b", 150)),
                    200
                ]
                label = meta.get("label", meta.get("variant", ""))
                
            else:
                # Fallback for state nodes
                variant = meta.get("variant", "?")
                radius = float(meta.get("latency", 1.0)) * 10
                color = _color_for_variant(variant)
                label = meta.get("label", "")
                
            radii.append(radius)
            colors_nodes.append(color)
            labels.append(label)
        
        # Log nodes with labels
        rr.points2d(
            f"{base}/nodes",
            positions,
            radii=radii,
            colors=colors_nodes,
            labels=labels if any(labels) else None,
            timeless=True
        )
        
        # Enhanced edges with different styles
        if edges:
            strips: List[List[List[float]]] = []
            colors_edges: List[List[int]] = []
            
            for i, j in edges:
                try:
                    p1 = positions[i]
                    p2 = positions[j]
                    strips.append([[float(p1[0]), float(p1[1])], [float(p2[0]), float(p2[1])]])
                    
                    # Color based on source node type
                    source_type = node_meta[i].get("kind", "state")
                    if source_type == "agent":
                        # Agent interactions are colored
                        color = [
                            int(node_meta[i].get("color_r", 100)),
                            int(node_meta[i].get("color_g", 100)),
                            int(node_meta[i].get("color_b", 200)),
                            150
                        ]
                    else:
                        # Other edges are semi-transparent gray
                        color = [150, 150, 150, 100]
                    
                    colors_edges.append(color)
                except Exception:
                    continue
                    
            if strips:
                rr.line_strips2d(f"{base}/edges", strips, colors=colors_edges, timeless=True)
        
        # Bounds
        bounds = [[-500, -500], [500, -500], [500, 500], [-500, 500], [-500, -500]]
        rr.line_strips2d(f"{base}/bounds", [bounds], timeless=True)
        
    except Exception as e:
        logger.debug("_log_graph_static_enhanced failed: %s", e)

def log_graph_static(
    rollout_id: str,
    positions: List[Tuple[float, float]],
    node_meta: List[Dict[str, str]],
    edges: List[Tuple[int, int]],
) -> None:
    """Timeless static graph - now enhanced version."""
    _log_graph_static_enhanced(rollout_id, positions, node_meta, edges)

def log_graph_events(
    rollout_id: str,
    events: List[Dict[str, Any]],
    *,
    timeline: str = "step",
) -> None:
    """Bright animated edge + destination point at each event time."""
    try:
        base = f"{_rollout_path(rollout_id)}/graph"

        for ev in events:
            t = float(ev["t"])
            variant = str(ev.get("variant", "?"))

            # Stamp ONLY the requested timeline (default: 'step')
            rr.set_time_seconds(timeline, t)

            strips = [[ev["p1"], ev["p2"]]]
            r, g, b, _ = _color_for_variant(variant)
            rr.line_strips2d(f"{base}/playhead_edge", strips, colors=[[r, g, b, 230]])
            rr.points2d(f"{base}/playhead_node", [ev["p2"]], radii=[12.0], colors=[[r, g, b, 240]], labels=None)

    except Exception as e:
        logger.debug("log_graph_events failed: %s", e)

# -----------------------------------------------------------------------------
# Rollout-level logging
# -----------------------------------------------------------------------------

def log_rollout_start(rollout_id: str, teams: int, total_variants: int, config: Dict[str, Any]) -> None:
    """
    Record a 'started' marker + rollout config at the rollout root.
    """
    base = _rollout_path(rollout_id)
    try:
        rr.kv(
            f"{base}/meta",
            timeless=True,
            status="started",
            teams=int(teams),
            total_variants=int(total_variants),
            start_time=config.get("start_time"),
        )
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
        rr.json_doc(
            f"{_rollout_path(rollout_id)}/pareto/{team_id}_{variant_id}",
            {"team": team_id, "variant": variant_id, "score": float(score), "cost": float(cost), "tokens": int(tokens), "label": f"{team_id}/{variant_id}"},
        )
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
              Spatial2DView           -> /graph/**  (WORLD graph: all teams)
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

        # Single pane listing ALL team logs (no tabs)
        teams_container = TeamPaneView(
            origin=rr.abs_path(f"{_rollout_path(rollout_id)}/stacks"),
            name="Team logs",
        )

        metrics_doc = rrb.TextDocumentView(
            origin=rr.abs_path(f"{_rollout_path(rollout_id)}/reports/metrics_cli"),
            name="Metrics (CLI)",
        )

        right = rrb.Vertical(graph_view, teams_container, metrics_doc)
        bp = rrb.Blueprint(rrb.Horizontal(left, right), collapse_panels=True)

        rr.send_blueprint(bp, make_active=make_active, make_default=make_default)

        # Best-effort: prime the time axis so the graph shows up immediately
        try:
            rr.set_time_seconds("step", 0.0)
        except Exception:
            pass

    except Exception as e:
        logger.debug("send_rollout_blueprint failed: %s", e)
