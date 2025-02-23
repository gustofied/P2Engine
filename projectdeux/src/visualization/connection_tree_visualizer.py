#!/usr/bin/env python3
"""
Visualize entity connections using rerun.

This script loads connection data from a JSON file, builds node and edge lists,
and visualizes them using Rerun's GraphView with proper edge connections.
"""

import json
import math
import rerun as rr
import rerun.blueprint as rrb
from rerun.blueprint import VisualBounds2D


def visualize_connections_from_data(data: dict, output_blueprint: bool = True):
    """
    Visualizes entity connections as a graph using Rerun.
    
    Args:
        data: Dictionary containing entity data with "entities" key
        output_blueprint: Whether to send a view layout blueprint to Rerun
    """
    entities = data.get("entities", [])
    
    # Build node lists
    node_ids = []
    labels = []
    positions = []
    n = len(entities)
    radius = 100.0  # Radius of the node circle arrangement
    
    for i, entity in enumerate(entities):
        node_ids.append(entity["id"])
        labels.append(f'{entity["entity_type"]}: {entity["name"]}')
        angle = 2 * math.pi * i / n if n > 0 else 0
        x = radius * math.cos(angle)
        y = radius * math.sin(angle)
        positions.append((x, y))
    
    # Build edge lists (source and target nodes)
    source_nodes = []
    target_nodes = []
    for entity in entities:
        source_id = entity["id"]
        for target_id in entity.get("connections", []):
            source_nodes.append(source_id)
            target_nodes.append(target_id)
    
    # Combine into a single list of edge tuples
    edges = list(zip(source_nodes, target_nodes))
    
    # Initialize Rerun
    rr.init("entity_connection_tree", spawn=True)
    
    # Log nodes to the visualization
    rr.log(
        "graph/nodes",
        rr.GraphNodes(
            node_ids=node_ids,
            labels=labels,
            positions=positions,
        ),
    )
    
    # Log edges using the new API format
    rr.log(
        "graph/edges",
        rr.GraphEdges(
            edges=edges,
            graph_type="directed",  # Use "undirected" if that's more appropriate
        ),
    )
    
    if output_blueprint:
        # Create a GraphView blueprint with appropriate bounds
        blueprint = rrb.Blueprint(
            rrb.GraphView(
                origin="/graph",
                name="Entity Connections",
                visual_bounds=VisualBounds2D(x_range=[-150, 150], y_range=[-150, 150]),
            ),
            collapse_panels=True,
        )
        rr.send_blueprint(blueprint)
    
    print("Visualization launched in Rerun viewer.")


def main():
    # Load connection data from JSON file
    JSON_FILE = "../../logs/litellm_log_20250221_144634.json"
    
    try:
        with open(JSON_FILE, "r") as f:
            run_data = json.load(f)
    except FileNotFoundError:
        print(f"Error: File not found - {JSON_FILE}")
        return
    except json.JSONDecodeError:
        print(f"Error: Invalid JSON in file - {JSON_FILE}")
        return

    # Convert agent data to entity format
    entities = []
    for agent_id, agent_data in run_data.get("agents", {}).items():
        name = agent_id  # default to agent ID
        entity_type = "agent"
        
        if agent_data.get("calls"):
            first_call = agent_data["calls"][0]
            if first_call.get("pre"):
                pre_event = first_call["pre"][0]
                metadata = pre_event.get("litellm_params", {}).get("metadata", {})
                name = metadata.get("agent_name", agent_id)
        
        entities.append({
            "id": agent_id,
            "name": name,
            "entity_type": entity_type,
            "connections": []  # Add actual connections here if available
        })
    
    # Generate and visualize the connection data
    connection_data = {"entities": entities}
    visualize_connections_from_data(connection_data)


if __name__ == "__main__":
    main()
