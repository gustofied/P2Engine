import os
import json
import datetime
import atexit

def make_json_serializable(obj):
    """
    Recursively convert non-serializable objects (like functions) to strings.
    """
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
    """
    Generate a run ID based on the current date and time.
    """
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# Global run identifier.
RUN_ID = get_run_id()

# Global log data structured by agent and by call.
GLOBAL_LOG_DATA = {
    "run_id": RUN_ID,
    "agents": {}  # each agent_id will map to {"calls": [ { "pre": [...], "post": [...] }, ... ]}
}

# Global dictionary to track the current call index for each agent.
CURRENT_CALL_INDEX = {}

def flush_logs():
    """
    Flush the global log data to a JSON file.
    """
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    log_file = os.path.join(log_dir, f"litellm_log_{RUN_ID}.json")
    with open(log_file, "w") as f:
        json.dump(GLOBAL_LOG_DATA, f, indent=2)
    print(f"Flushed logs to {log_file}")

# Register flush_logs to be called at program exit.
atexit.register(flush_logs)

def extract_agent_id(payload: dict) -> str:
    """
    Attempt to extract an agent ID from the payload.
    First check top-level 'metadata'; if not found, try inside 'litellm_params'.
    Otherwise, default to "unknown_agent".
    """
    agent_id = "unknown_agent"
    if "metadata" in payload and isinstance(payload["metadata"], dict):
        agent_id = payload["metadata"].get("agent_id", "unknown_agent")
    elif "litellm_params" in payload and isinstance(payload["litellm_params"], dict):
        # Sometimes metadata might be nested in litellm_params.
        meta = payload["litellm_params"].get("metadata", {})
        if isinstance(meta, dict):
            agent_id = meta.get("agent_id", "unknown_agent")
    return agent_id

def my_custom_logging_fn(model_call_dict: dict) -> None:
    """
    Custom logging function for litellm API calls.

    It groups log events by agent and by call. For a 'pre' event, a new call record is started.
    For a 'post' event, the event is added to the most recent call for that agent.
    """
    # Convert payload to a JSON-serializable form.
    serializable_payload = make_json_serializable(model_call_dict)
    serializable_payload["logged_at"] = datetime.datetime.now().isoformat()
    
    # Determine the event type from the payload.
    event_type = serializable_payload.get("log_event_type", "unknown_event")
    
    # Classify event as 'pre' if it contains "pre", otherwise 'post'.
    category = "pre" if "pre" in event_type.lower() else "post"
    
    # Extract agent ID from the payload.
    agent_id = extract_agent_id(serializable_payload)
    
    # Initialize log storage for this agent if necessary.
    if agent_id not in GLOBAL_LOG_DATA["agents"]:
        GLOBAL_LOG_DATA["agents"][agent_id] = {"calls": []}
    
    # For a pre event, start a new call.
    if category == "pre":
        call_entry = {"pre": [serializable_payload], "post": []}
        GLOBAL_LOG_DATA["agents"][agent_id]["calls"].append(call_entry)
        # Save index of this new call.
        CURRENT_CALL_INDEX[agent_id] = len(GLOBAL_LOG_DATA["agents"][agent_id]["calls"]) - 1
    else:
        # For a post event, add to the most recent call.
        if agent_id in CURRENT_CALL_INDEX:
            idx = CURRENT_CALL_INDEX[agent_id]
            GLOBAL_LOG_DATA["agents"][agent_id]["calls"][idx]["post"].append(serializable_payload)
        else:
            # If no current call exists, create a new one with an empty pre list.
            call_entry = {"pre": [], "post": [serializable_payload]}
            GLOBAL_LOG_DATA["agents"][agent_id]["calls"].append(call_entry)
            CURRENT_CALL_INDEX[agent_id] = len(GLOBAL_LOG_DATA["agents"][agent_id]["calls"]) - 1
