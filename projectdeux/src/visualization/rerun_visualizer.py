#!/usr/bin/env python3

import json
import rerun as rr
import rerun.blueprint as rrb


def main():
    # --------------------------------------------------------------------------
    # 1) Load your JSON from file
    # --------------------------------------------------------------------------
    JSON_FILE = "../../logs/litellm_log_20250221_144634.json"  
    with open(JSON_FILE, "r") as f:
        run_data = json.load(f)

    # --------------------------------------------------------------------------
    # 2) Initialize Rerun
    # --------------------------------------------------------------------------
    rr.init("agent_graph_and_text_logs", spawn=True)

    # --------------------------------------------------------------------------
    # 3) Create Graph Nodes from your JSON
    #
    #    - We'll collect the agent names & spread them out horizontally.
    #    - We'll also log the entire JSON for reference in the Rerun hierarchy.
    # --------------------------------------------------------------------------
    agent_names = list(run_data["agents"].keys())  # e.g. ["SimpleAgent", "ChaosAgent", ...]

    # Let's space them out on the x-axis in increments of ~100 units
    node_positions = [(float(i * 100), 0.0) for i in range(len(agent_names))]

    # Log the agent nodes:
    rr.log(
        "graph",
        rr.GraphNodes(
            node_ids=agent_names,
            labels=agent_names,       # Just use their names as labels
            positions=node_positions, # A simple 1D line layout
        ),
    )

    # Also log the entire run_data so you can inspect it in Rerun's hierarchy:
    rr.log("raw/run_data", run_data)

    # --------------------------------------------------------------------------
    # 4) Parse "calls" from JSON and log them as TextLog lines
    #
    #    We'll log to "logs/<agent_name>" so each agent has its own sub-stream.
    #
    #    For example, for each "pre" -> [PRE] role: content
    #                   and for each "post" -> [POST] role: content
    # --------------------------------------------------------------------------
    for agent_name, agent_data in run_data["agents"].items():
        calls = agent_data.get("calls", [])
        for call in calls:
            # "pre" events
            for pre_event in call.get("pre", []):
                for msg in pre_event.get("messages", []):
                    role = msg.get("role", "UNKNOWN")
                    content = msg.get("content", "")
                    line = f"[PRE] {role.upper()}: {content}"
                    rr.log(f"logs/{agent_name}", rr.TextLog(line, level=rr.TextLogLevel.INFO))

            # "post" events
            for post_event in call.get("post", []):
                for msg in post_event.get("messages", []):
                    role = msg.get("role", "UNKNOWN")
                    content = msg.get("content", "")
                    line = f"[POST] {role.upper()}: {content}"
                    rr.log(f"logs/{agent_name}", rr.TextLog(line, level=rr.TextLogLevel.INFO))

    # --------------------------------------------------------------------------
    # 5) Create a blueprint that puts the GraphView and TextLogView side by side
    #
    #    We'll use a Horizontal container with 2 children:
    #      - GraphView (left)
    #      - TextLogView (right)
    #
    #    By default, each child gets half the width; you can pass `column_shares`
    #    to control relative sizing (e.g., [3, 2], meaning 3/5 width vs 2/5).
    # --------------------------------------------------------------------------
    blueprint = rrb.Blueprint(
        rrb.Horizontal(
            rrb.GraphView(
                origin="/graph",
                name="Agent Graph",
            ),
            rrb.TextLogView(
                origin="/logs",
                name="Agent Logs",
            ),
            column_shares=[1.0, 1.0],  # 50/50; tweak as needed, e.g. [3.0, 2.0]
        ),
        # If you want to hide the blueprint/selection panels and see only
        # your two main views, set collapse_panels=True. Otherwise, you can
        # see them in separate panels. 
        collapse_panels=False,
    )

    # --------------------------------------------------------------------------
    # 6) Send the blueprint
    #
    #    This instructs Rerun to show a single horizontal container
    #    with two sub-panels: "Agent Graph" and "Agent Logs".
    # --------------------------------------------------------------------------
    rr.send_blueprint(blueprint)

    # --------------------------------------------------------------------------
    print("Rerun logging complete! Check your viewer for side-by-side Graph & Logs.")


if __name__ == "__main__":
    main()
