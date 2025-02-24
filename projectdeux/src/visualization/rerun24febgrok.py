#!/usr/bin/env python3
"""
Dynamic Network and Message Tree Visualization using Rerun

This script visualizes a dynamic network graph, message log, and message tree. It supports two JSON formats:
1. Old Format: A dictionary with 'messages' containing a list of messages.
2. New Format: A list with a dictionary containing 'interactions' and 'entities'.

Usage: python script.py --config <path_to_json_file>
"""

import json
import datetime
import argparse
import logging
from typing import Dict, List, Tuple, Any

import rerun as rr
import rerun.blueprint as rrb
from rerun.blueprint.archetypes.force_link import ForceLink
from rerun.blueprint.archetypes.force_many_body import ForceManyBody

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Predefined colors for agents
AGENT_COLORS = [
    [0, 0, 255],    # Blue
    [255, 0, 0],    # Red
    [0, 255, 0],    # Green
    [255, 255, 0],  # Yellow
    [255, 0, 255],  # Magenta
    [0, 255, 255],  # Cyan
    [128, 0, 0],    # Maroon
    [0, 128, 0],    # Olive
    [0, 0, 128],    # Navy
    [128, 128, 0],  # Olive
]

def log_network_graph(nodes: Dict[str, Dict[str, Any]], edges: List[Tuple[str, str]]) -> None:
    """Log the network graph to Rerun."""
    node_ids = list(nodes.keys())
    labels = [nodes[nid]["label"] for nid in node_ids]
    colors = [rr.components.Color(nodes[nid]["color"]) for nid in node_ids]
    rr.log(
        "agent-communication/network_graph",
        rr.GraphNodes(node_ids=node_ids, colors=colors, labels=labels),
        rr.GraphEdges(edges=edges, graph_type="directed")
    )

def log_message_tree(node_ids: List[str], labels: List[str], colors: List[rr.components.Color], edges: List[Tuple[str, str]]) -> None:
    """Log the message tree graph to Rerun."""
    rr.log(
        "agent-communication/message_tree",
        rr.GraphNodes(node_ids=node_ids, colors=colors, labels=labels),
        rr.GraphEdges(edges=edges, graph_type="directed")
    )

def update_nodes_for_message(nodes: Dict[str, Dict[str, Any]], sender: str, receiver: str) -> None:
    """Add sender and receiver to network nodes if they don’t exist, using a default color."""
    default_color = [0, 255, 0]  # Green for new nodes
    for agent in (sender, receiver):
        if agent not in nodes:
            nodes[agent] = {"label": agent, "color": default_color}
            logger.info(f"Added new node: {agent}")

def create_blueprint() -> None:
    """Create a three-panel blueprint for Rerun."""
    grid_blueprint = rrb.Blueprint(
        rrb.Grid(
            rrb.GraphView(
                origin="agent-communication/network_graph",
                name="Dynamic Network Graph",
                force_link=ForceLink(distance=260),
                force_many_body=ForceManyBody(strength=-60)
            ),
            rrb.TextLogView(
                origin="agent-communication/messages",
                name="Message Log"
            ),
            rrb.GraphView(
                origin="agent-communication/message_tree",
                name="Message Tree",
                force_link=ForceLink(distance=150),
                force_many_body=ForceManyBody(strength=-60)
            )
        ),
        collapse_panels=False
    )
    rr.send_blueprint(grid_blueprint)

def process_messages(initial_nodes: Dict[str, Dict[str, Any]], messages: List[Dict[str, Any]]) -> None:
    """
    Process standardized messages to update the network graph and message tree.

    Args:
        initial_nodes: Initial dictionary of network nodes.
        messages: List of standardized message dictionaries with 'sender', 'receiver', 'content', 'time'.
    """
    network_nodes = initial_nodes.copy()
    network_edges: List[Tuple[str, str]] = []
    message_tree_node_ids: List[str] = []
    message_tree_labels: List[str] = []
    message_tree_colors: List[rr.components.Color] = []
    message_tree_edges: List[Tuple[str, str]] = []

    rr.log("agent-communication/messages", timeless=True)

    base_time = None
    for i, msg in enumerate(messages):
        sender = msg["sender"]
        receiver = msg["receiver"]
        content = msg["content"]
        time_str = msg["time"]

        # Set timeline
        if time_str:
            try:
                msg_time = datetime.datetime.fromisoformat(time_str)
               ...

Something went wrong, please try again.