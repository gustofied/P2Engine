# File: src/visualization/rerun_visualizer.py

import json
import os
import rerun as rr
import rerun.blueprint as rrb

def load_log_file(log_filepath: str) -> dict:
    with open(log_filepath, "r") as f:
        return json.load(f)

def build_graph_data(log_data: dict):
    """
    Convert the log data into nodes and edges.
    Nodes: each agent.
    Edges: each API call represented as an edge from pre-event to post-event, with timestamps.
    """
    nodes = []
    edges = []
    
    agents = log_data.get("agents", {})
    for agent_id, data in agents.items():
        # Create a node for each agent.
        nodes.append({"id": agent_id, "label": agent_id})
        
        # For each call, create edges from pre to post.
        for call in data.get("calls", []):
            # For simplicity, assume one pre and one post event per call.
            # In practice, you can create multiple edges (or annotate the call with counts).
            if call.get("pre") and call.get("post"):
                pre_event = call["pre"][0]
                post_event = call["post"][0]
                edges.append({
                    "from": agent_id,
                    "to": agent_id,  # if self-contained; otherwise, if you have cross-agent calls, adjust accordingly.
                    "label": f"{pre_event.get('log_event_type')} -> {post_event.get('log_event_type')}",
                    "start": pre_event.get("logged_at"),
                    "end": post_event.get("logged_at")
                })
    return nodes, edges

def send_to_rerun(nodes, edges):
    rr.init("log_visualization", spawn=True)
    
    # Log nodes
    rr.log(
        "agents/nodes",
        rr.GraphNodes(
            node_ids=[node["id"] for node in nodes],
            positions=[(0.0, 0.0)] * len(nodes),  # For now, place nodes arbitrarily; you can later compute positions.
            labels=[node["label"] for node in nodes]
        )
    )
    
    # Log edges
    rr.log(
        "agents/edges",
        rr.GraphEdges(
            edge_ids=[f"{edge['from']}-{edge['to']}-{i}" for i, edge in enumerate(edges)],
            connections=[(edge["from"], edge["to"]) for edge in edges],
            labels=[edge["label"] for edge in edges]
        )
    )
    
    # Create a simple GraphView blueprint.
    blueprint = rrb.Blueprint(
        rrb.GraphView(
            origin="/agents",
            name="Agent Graph",
            visual_bounds=rrb.VisualBounds2D(x_range=[-150, 150], y_range=[-150, 150])
        ),
        collapse_panels=True,
    )
    rr.send_blueprint(blueprint)

def visualize_log(log_filepath: str):
    log_data = load_log_file(log_filepath)
    nodes, edges = build_graph_data(log_data)
    send_to_rerun(nodes, edges)

if __name__ == "__main__":
    # For testing, specify your log file path here.
    log_file = os.path.join("logs", "litellm_log_YOUR_RUN_ID.json")
    visualize_log(log_file)

