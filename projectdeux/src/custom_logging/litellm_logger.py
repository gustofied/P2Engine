import os
import json
import datetime
import atexit

def make_json_serializable(obj):
    if isinstance(obj, dict):
        return {k: make_json_serializable(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [make_json_serializable(item) for item in obj]
    else:
        try:
            json.dumps(obj)
            return obj
        except (TypeError, OverflowError):
            return str(obj)

def get_run_id():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

RUN_ID = get_run_id()

GLOBAL_LOG_DATA = {
    "run_id": RUN_ID,
    "agents": {}
}

CURRENT_CALL_INDEX = {}

def flush_logs():
    print(f"Flushing GLOBAL_LOG_DATA: {GLOBAL_LOG_DATA}")
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, f"litellm_log_{RUN_ID}.json")
    with open(log_file, "w") as f:
        json.dump(GLOBAL_LOG_DATA, f, indent=2)
    print(f"Flushed logs to {log_file}")

def extract_agent_id(payload: dict) -> str:
    agent_id = "unknown_agent"
    if "metadata" in payload and isinstance(payload["metadata"], dict):
        agent_id = payload["metadata"].get("agent_id", "unknown_agent")
    elif "litellm_params" in payload and isinstance(payload["litellm_params"], dict):
        meta = payload["litellm_params"].get("metadata", {})
        if isinstance(meta, dict):
            agent_id = meta.get("agent_id", "unknown_agent")
    return agent_id

def my_custom_logging_fn(model_call_dict: dict) -> None:
    print("Custom logging function called with:", model_call_dict)
    serializable_payload = make_json_serializable(model_call_dict)
    serializable_payload["logged_at"] = datetime.datetime.now().isoformat()
    event_type = serializable_payload.get("log_event_type", "unknown_event")
    category = "pre" if "pre" in event_type.lower() else "post"
    agent_id = extract_agent_id(serializable_payload)
    print(f"Agent ID: {agent_id}, Category: {category}")
    if agent_id not in GLOBAL_LOG_DATA["agents"]:
        GLOBAL_LOG_DATA["agents"][agent_id] = {"calls": []}
    if category == "pre":
        call_entry = {"pre": [serializable_payload], "post": []}
        GLOBAL_LOG_DATA["agents"][agent_id]["calls"].append(call_entry)
        CURRENT_CALL_INDEX[agent_id] = len(GLOBAL_LOG_DATA["agents"][agent_id]["calls"]) - 1
    else:
        if agent_id in CURRENT_CALL_INDEX:
            idx = CURRENT_CALL_INDEX[agent_id]
            GLOBAL_LOG_DATA["agents"][agent_id]["calls"][idx]["post"].append(serializable_payload)
        else:
            call_entry = {"pre": [], "post": [serializable_payload]}
            GLOBAL_LOG_DATA["agents"][agent_id]["calls"].append(call_entry)
            CURRENT_CALL_INDEX[agent_id] = len(GLOBAL_LOG_DATA["agents"][agent_id]["calls"]) - 1
    print(f"Updated GLOBAL_LOG_DATA: {GLOBAL_LOG_DATA}")