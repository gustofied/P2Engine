#!/usr/bin/env python3
"""
Dynamic Network and Message Tree Visualization using Rerun

This script demonstrates a dynamic network graph and a message tree,
where new nodes can be added after the initial state. It shows three views:
1. A Dynamic Network Graph that displays agents and their evolving connections.
2. A Message Log that displays individual messages.
3. A Message Tree that builds a sequential chain of message nodes with simplified labels.

Configuration can be provided via a JSON file using the --config command-line argument.
If no file is provided, a default configuration is used.
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

# Configure logging for debugging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def log_network_graph(nodes: Dict[str, Dict[str, Any]], edges: List[Tuple[str, str]]) -> None:
    """
    Log the network graph to Rerun.

    Args:
        nodes: A dictionary mapping node ids to a dict with keys "label" and "color".
        edges: A list of tuples (source, target) representing graph edges.
    """
    node_ids = list(nodes.keys())
    labels = [nodes[nid]["label"] for nid in node_ids]
    colors = [rr.components.Color(nodes[nid]["color"]) for nid in node_ids]
    rr.log(
        "agent-communication/network_graph",
        rr.GraphNodes(node_ids=node_ids, colors=colors, labels=labels),
        rr.GraphEdges(edges=edges, graph_type="directed")
    )

def log_message_tree(node_ids: List[str], labels: List[str], colors: List[rr.components.Color], edges: List[Tuple[str, str]]) -> None:
    """
    Log the message tree graph to Rerun.

    Args:
        node_ids: List of node IDs.
        labels: List of simplified labels (e.g., "Msg 1", "Msg 2").
        colors: List of rr.components.Color instances.
        edges: List of tuples (source, target) representing graph edges.
    """
    rr.log(
        "agent-communication/message_tree",
        rr.GraphNodes(node_ids=node_ids, colors=colors, labels=labels),
        rr.GraphEdges(edges=edges, graph_type="directed")
    )

def update_nodes_for_message(nodes: Dict[str, Dict[str, Any]], sender: str, receiver: str) -> None:
    """
    Ensure that both the sender and receiver exist in the network.
    If either is missing, add it with a default configuration.

    Args:
        nodes: Current dictionary of network nodes.
        sender: The sender agent name.
        receiver: The receiver agent name.
    """
    default_color = [0, 255, 0]  # Default color for new nodes: green
    for agent in (sender, receiver):
        if agent not in nodes:
            nodes[agent] = {"label": agent, "color": default_color}
            logger.info(f"Added new node: {agent}")

def create_blueprint() -> None:
    """
    Create and send a blueprint with three views:
    1. Dynamic Network Graph
    2. Message Log
    3. Message Tree
    """
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

def process_messages(messages: List[Dict[str, Any]]) -> None:
    """
    Process messages to update the dynamic network graph and message tree.

    Args:
        messages: A list of message dictionaries.
    """
    # Initialize state for network nodes and edges.
    network_nodes: Dict[str, Dict[str, Any]] = {
        "SimpleAgent": {"label": "SimpleAgent", "color": [0, 0, 255]},
        "ChaosAgent": {"label": "ChaosAgent", "color": [255, 0, 0]}
    }
    network_edges: List[Tuple[str, str]] = []

    # Initialize state for the message tree graph.
    message_tree_node_ids: List[str] = []
    message_tree_labels: List[str] = []  # Simplified labels (e.g., "Msg 1")
    message_tree_colors: List[rr.components.Color] = []
    message_tree_edges: List[Tuple[str, str]] = []

    # Log a parent node for messages so the view can locate them.
    rr.log("agent-communication/messages", timeless=True)

    base_time = None
    for i, msg in enumerate(messages):
        sender = msg["from"]
        receiver = msg["to"]
        text = msg["text"]

        # Set the time based on the message's start_time.
        start_time_str = msg.get("start_time")
        if start_time_str:
            msg_time = datetime.datetime.fromisoformat(start_time_str)
            if base_time is None:
                base_time = msg_time
            dt_seconds = (msg_time - base_time).total_seconds()
            rr.set_time_seconds("time", dt_seconds)
        else:
            rr.set_time_sequence("time", i)

        # Log the individual full text message.
        rr.log(
            f"agent-communication/messages/msg_{i}",
            rr.TextLog(f"{sender} -> {receiver}: {text}")
        )

        # Update network nodes if new agents appear.
        update_nodes_for_message(network_nodes, sender, receiver)

        # Add a new edge to the network graph.
        network_edges.append((sender, receiver))
        log_network_graph(network_nodes, network_edges)

        # Update the message tree: add a new node with a simplified label.
        msg_node_id = f"msg_{i}"
        message_tree_node_ids.append(msg_node_id)
        # Use a simplified label like "Msg 1", "Msg 2", etc.
        message_tree_labels.append(f"Msg {i + 1}")
        # Choose node color based on sender.
        if sender == "SimpleAgent":
            color = [0, 0, 255]
        elif sender == "ChaosAgent":
            color = [255, 0, 0]
        else:
            color = [0, 255, 0]
        message_tree_colors.append(rr.components.Color(color))
        # Connect this message node to the previous one to form a sequential chain.
        if i > 0:
            message_tree_edges.append((f"msg_{i-1}", msg_node_id))
        log_message_tree(message_tree_node_ids, message_tree_labels, message_tree_colors, message_tree_edges)

def load_config(json_file: str = None) -> Dict[str, Any]:
    """
    Load configuration from a JSON file if provided, otherwise use a default configuration.

    Args:
        json_file: Optional; path to the JSON configuration file.
    Returns:
        Parsed configuration as a dictionary.
    """
    if json_file:
        try:
            with open(json_file, "r") as f:
                config = json.load(f)
            logger.info(f"Loaded configuration from {json_file}")
            return config
        except Exception as e:
            logger.error(f"Error loading JSON config from {json_file}: {e}")
            raise
    else:
        # Default configuration.
        default_json = '''
        {
            "messages": [
                {"from": "SimpleAgent", "to": "ChaosAgent", "text": "Hello from SimpleAgent!", "start_time": "2025-02-23 09:57:59.756215"},
                {"from": "ChaosAgent", "to": "SimpleAgent", "text": "Hi there, ChaosAgent at your service.", "start_time": "2025-02-23 09:58:00.756215"},
                {"from": "SimpleAgent", "to": "NewAgent", "text": "Welcome, NewAgent!", "start_time": "2025-02-23 09:58:01.756215"},
                {"from": "NewAgent", "to": "ChaosAgent", "text": "Thank you! Happy to join.", "start_time": "2025-02-23 09:58:02.756215"}
            ]
        }
        '''
        logger.info("Using default configuration")
        return json.loads(default_json)

def main() -> None:
    """
    Main entry point for the dynamic visualization.
    """
    parser = argparse.ArgumentParser(description="Dynamic Network and Message Tree Visualization using Rerun.")
    parser.add_argument("--config", type=str, help="Path to JSON configuration file", default=None)
    args = parser.parse_args()

    config = load_config(args.config)

    # Initialize Rerun.
    rr.init("viz-tool", spawn=True)

    # Log initial empty state for graphs at time 0.
    rr.set_time_sequence("time", 0)
    log_network_graph({
        "SimpleAgent": {"label": "SimpleAgent", "color": [0, 0, 255]},
        "ChaosAgent": {"label": "ChaosAgent", "color": [255, 0, 0]}
    }, [])
    log_message_tree([], [], [], [])

    # Process messages to update the graphs dynamically.
    process_messages(config.get("messages", []))

    # Create and send the blueprint for the three-panel view.
    create_blueprint()

if __name__ == "__main__":
    main()
