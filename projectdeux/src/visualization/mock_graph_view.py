#!/usr/bin/env python3
"""
Enhanced Agent Graph Visualization with Full GraphView Customization

This script creates a sample dataset of agents with connections between them.
Each agent is converted to a node with enhanced visual properties (colors, radii, etc.).
Edges are created based on each agent's "connections" list.
A customized GraphView blueprint is then created using:
  - A contents query,
  - Advanced force layout settings.
"""

import math
import rerun as rr
import rerun.blueprint as rrb
from rerun.blueprint import VisualBounds2D

# Import the force layout archetypes from the blueprint's archetypes.
from rerun.blueprint.archetypes import ForceLink, ForceManyBody, ForcePosition, ForceCollisionRadius, ForceCenter

def hex_to_rgba(hex_str, alpha=255):
    """Convert a hex color (e.g. '#FF5733') into an RGBA tuple."""
    hex_str = hex_str.lstrip('#')
    if len(hex_str) == 6:
        r = int(hex_str[0:2], 16)
        g = int(hex_str[2:4], 16)
        b = int(hex_str[4:6], 16)
        return (r, g, b, alpha)
    elif len(hex_str) == 3:
        r = int(hex_str[0]*2, 16)
        g = int(hex_str[1]*2, 16)
        b = int(hex_str[2]*2, 16)
        return (r, g, b, alpha)
    else:
        raise ValueError("Invalid hex color format")

def visualize_enhanced_graph(data: dict, output_blueprint: bool = True):
    """
    Visualizes agent connections as an enhanced graph with extra visual properties and customization.
    
    Expects the data to have an "entities" key with each entity containing:
      - "id"
      - "name"
      - "entity_type"
      - "connections": a list of other entity IDs
       
    Args:
        data: Dictionary containing the entities.
        output_blueprint: Whether to send a customized GraphView blueprint.
    """
    entities = data.get("entities", [])
    
    # Build node lists.
    node_ids = []
    labels = []
    positions = []
    colors = []  # List of RGBA tuples.
    radii = []   # Radii for each node.
    
    n = len(entities)
    arrange_radius = 150.0  # For arranging nodes in a circle.
    default_hex_colors = ["#FF5733", "#33FF57", "#3357FF", "#FF33A1", "#A133FF", "#33FFF0"]
    
    for i, entity in enumerate(entities):
        node_ids.append(entity["id"])
        labels.append(f'{entity["entity_type"]}: {entity["name"]}')
        # Arrange nodes evenly in a circle.
        angle = (2 * math.pi * i / n) if n > 0 else 0
        x = arrange_radius * math.cos(angle)
        y = arrange_radius * math.sin(angle)
        positions.append((x, y))
        # Convert hex color to an RGBA tuple.
        colors.append(hex_to_rgba(default_hex_colors[i % len(default_hex_colors)]))
        # Assign a radii value (example: 10, 15, or 20).
        radii.append(10 + 5 * (i % 3))
    
    # Build the edge list from each entity's "connections" field.
    edges = []
    for entity in entities:
        source_id = entity["id"]
        for target_id in entity.get("connections", []):
            edges.append((source_id, target_id))
    
    # Initialize Rerun.
    rr.init("enhanced_agent_graph", spawn=True)
    
    # Log nodes with enhanced visual properties.
    rr.log(
        "graph/nodes",
        rr.GraphNodes(
            node_ids=node_ids,
            labels=labels,
            positions=positions,
            colors=colors,    # List of RGBA tuples.
            radii=radii,      # Use the keyword "radii".
        ),
    )
    
    # Log the edges.
    rr.log(
        "graph/edges",
        rr.GraphEdges(
            edges=edges,
            graph_type="directed",  # Change to "undirected" if desired.
        ),
    )
    
    # Instantiate force layout objects.
    fl = ForceLink()
    fl.enabled = True
    fl.distance = 120.0
    fl.iterations = 5

    fmb = ForceManyBody()
    fmb.enabled = True
    fmb.strength = -30

    fp = ForcePosition()
    fp.enabled = True
    fp.strength = 0.1
    fp.position = (0, 0)

    fcr = ForceCollisionRadius()
    fcr.enabled = True
    fcr.strength = 0.5
    fcr.iterations = 2

    fc = ForceCenter()
    fc.enabled = True
    fc.strength = 0.3
    
    # Create a customized blueprint.
    blueprint = rrb.Blueprint(
        rrb.GraphView(
            origin="/graph",
            name="Enhanced Agent Graph",
            contents="$origin/**",  # Automatically include all entities under the origin.
            visual_bounds=rrb.VisualBounds2D(x_range=[-200, 200], y_range=[-200, 200]),
            force_link=fl,
            force_many_body=fmb,
            force_position=fp,
            force_collision_radius=fcr,
            force_center=fc,
        ),
        collapse_panels=True
        # Defaults and overrides have been omitted as requested.
    )
    if output_blueprint:
        rr.send_blueprint(blueprint)
    
    print("Enhanced agent graph visualization launched in Rerun viewer.")

def main():
    # Create a sample dataset that mimics your JSON structure.
    sample_data = {
        "run_id": "20250222_103620",
        "agents": {
            "agent-1": {
                "calls": [{
                    "pre": [{
                        "litellm_params": {"metadata": {"agent_name": "SimpleAgent"}},
                        "connections": ["agent-2", "agent-3"]
                    }]
                }]
            },
            "agent-2": {
                "calls": [{
                    "pre": [{
                        "litellm_params": {"metadata": {"agent_name": "ChaosAgent"}},
                        "connections": ["agent-3", "agent-4"]
                    }]
                }]
            },
            "agent-3": {
                "calls": [{
                    "pre": [{
                        "litellm_params": {"metadata": {"agent_name": "MysteriousAgent"}},
                        "connections": ["agent-1"]
                    }]
                }]
            },
            "agent-4": {
                "calls": [{
                    "pre": [{
                        "litellm_params": {"metadata": {"agent_name": "WiseAgent"}},
                        "connections": ["agent-1", "agent-3"]
                    }]
                }]
            }
        }
    }
    
    # Convert agent data to a list of entities.
    entities = []
    for agent_id, agent_data in sample_data.get("agents", {}).items():
        name = agent_id
        entity_type = "agent"
        connections = []
        if agent_data.get("calls"):
            first_call = agent_data["calls"][0]
            if first_call.get("pre"):
                pre_event = first_call["pre"][0]
                metadata = pre_event.get("litellm_params", {}).get("metadata", {})
                name = metadata.get("agent_name", agent_id)
                connections = pre_event.get("connections", [])
        entities.append({
            "id": agent_id,
            "name": name,
            "entity_type": entity_type,
            "connections": connections
        })
    
    connection_data = {"entities": entities}
    visualize_enhanced_graph(connection_data)

if __name__ == "__main__":
    main()
