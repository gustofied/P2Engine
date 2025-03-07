import os
import json
import datetime
import atexit
import logging
from typing import Optional, Dict

# Set up logger
logger = logging.getLogger("CentralLogger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

# Enhanced JSON serialization function
def make_json_serializable(obj):
    """Convert any object to a JSON-serializable format."""
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): make_json_serializable(v) for k, v in obj.items()}
    elif hasattr(obj, '__dict__'):  # Handle custom objects (e.g., BaseAgent)
        return make_json_serializable(obj.__dict__)
    else:
        return str(obj)  # Fallback for non-serializable objects

# Global run ID for log file naming
def get_run_id():
    return datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

RUN_ID = get_run_id()

class CentralLogger:
    def __init__(self):
        """Initialize the logger with empty log lists and tracking structures."""
        self.scenario_logs = []  # List to store all scenario logs
        self.interaction_logs = []  # List to store all interaction logs
        self.current_system_start_time = None  # Tracks the start time of the current system
        self.global_log_data = {
            "run_id": RUN_ID,
            "agents": {}  # For LiteLLM call tracking
        }
        self.current_call_index = {}  # Tracks the latest call index per agent

    def log_system_start(self, system_name: str, entities: dict, problem: str, goal: str, expected_result: str = None) -> None:
        """Log the start of a system with its details."""
        self.current_system_start_time = datetime.datetime.now()
        # Serialize entities (e.g., agents with components)
        entity_data = {
            entity_id: make_json_serializable(entity)
            for entity_id, entity in entities.items()
        }
        system_log = {
            "system_name": system_name,
            "start_time": self.current_system_start_time.isoformat(),
            "entities": entity_data,
            "problem": problem,
            "goal": goal,
            "expected_result": expected_result,
            "interactions": [],
            "time_spent": None,
            "result": None,
            "evaluation": None,
            "reward": None
        }
        self.scenario_logs.append(system_log)
        logger.info(f"System '{system_name}' started with goal: {goal}, Expected Result: {expected_result or 'Not specified'}")

    def log_interaction(self, sender: str, receiver: str, message: str, metadata: Optional[Dict] = None) -> None:
        """Log an interaction between entities."""
        interaction = {
            "from": sender,
            "to": receiver,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat(),
            "metadata": make_json_serializable(metadata) if metadata else {}
        }
        self.interaction_logs.append(interaction)
        if self.scenario_logs:
            self.scenario_logs[-1]["interactions"].append(interaction)
        logger.info(f"Interaction: {sender} -> {receiver}: {message[:50]}...")

    def extract_agent_id(self, payload: dict) -> str:
        """Extract agent ID from a LiteLLM payload."""
        agent_id = "unknown_agent"
        if "metadata" in payload and isinstance(payload["metadata"], dict):
            agent_id = payload["metadata"].get("agent_id", "unknown_agent")
        elif "litellm_params" in payload and isinstance(payload["litellm_params"], dict):
            meta = payload["litellm_params"].get("metadata", {})
            if isinstance(meta, dict):
                agent_id = meta.get("agent_id", "unknown_agent")
        return agent_id

    def log_litellm_event(self, model_call_dict: dict) -> None:
        """Log a LiteLLM event, integrating with global agent call tracking."""
        serializable_payload = make_json_serializable(model_call_dict)
        serializable_payload["logged_at"] = datetime.datetime.now().isoformat()
        event_type = serializable_payload.get("log_event_type", "unknown_event")
        category = "pre" if "pre" in event_type.lower() else "post"
        agent_id = self.extract_agent_id(serializable_payload)

        # Initialize agent in global log if not present
        if agent_id not in self.global_log_data["agents"]:
            self.global_log_data["agents"][agent_id] = {"calls": []}

        # Log pre/post events similar to my_custom_logging_fn
        if category == "pre":
            call_entry = {"pre": [serializable_payload], "post": []}
            self.global_log_data["agents"][agent_id]["calls"].append(call_entry)
            self.current_call_index[agent_id] = len(self.global_log_data["agents"][agent_id]["calls"]) - 1
        else:
            if agent_id in self.current_call_index:
                idx = self.current_call_index[agent_id]
                self.global_log_data["agents"][agent_id]["calls"][idx]["post"].append(serializable_payload)
            else:
                call_entry = {"pre": [], "post": [serializable_payload]}
                self.global_log_data["agents"][agent_id]["calls"].append(call_entry)
                self.current_call_index[agent_id] = len(self.global_log_data["agents"][agent_id]["calls"]) - 1

        logger.info(f"LiteLLM event logged for agent '{agent_id}': {model_call_dict.get('model', 'unknown')} ({category})")

    def log_system_end(self, result: str, evaluation: dict, reward: int, all_agents: dict) -> None:
        """Log the end of a system with its results."""
        if not self.scenario_logs or not self.current_system_start_time:
            logger.warning("No active system to end")
            return
        end_time = datetime.datetime.now()
        time_spent = (end_time - self.current_system_start_time).total_seconds()
        # Serialize all agents
        serialized_agents = make_json_serializable(all_agents)
        self.scenario_logs[-1].update({
            "time_spent": time_spent,
            "result": result,
            "evaluation": make_json_serializable(evaluation),
            "reward": reward,
            "entities": serialized_agents
        })
        logger.info(f"System ended. Time spent: {time_spent}s, Result: {result[:50]}..., Reward: {reward}")

    def get_logs(self):
        """Return the most recent scenario log."""
        if not self.scenario_logs:
            logger.warning("No scenario logs available to return")
            return {}
        return self.scenario_logs[-1]

    def flush_logs(self) -> None:
        """Write all logs to JSON files in the 'discovery' directory."""
        log_dir = "discovery"  # Updated from 'logs' to 'discovery'
        os.makedirs(log_dir, exist_ok=True)

        # Flush scenario logs
        scenario_serializable = make_json_serializable(self.scenario_logs)
        system_file = os.path.join(log_dir, f"system_log_{RUN_ID}.json")
        with open(system_file, "w") as f:
            json.dump(scenario_serializable, f, indent=2)
        logger.info(f"Flushed system logs to {system_file}")

        # Flush interaction logs
        interaction_serializable = make_json_serializable(self.interaction_logs)
        interaction_file = os.path.join(log_dir, f"interaction_log_{RUN_ID}.json")
        with open(interaction_file, "w") as f:
            json.dump(interaction_serializable, f, indent=2)
        logger.info(f"Flushed interaction logs to {interaction_file}")

        # Flush LiteLLM logs (global log data)
        global_serializable = make_json_serializable(self.global_log_data)
        litellm_file = os.path.join(log_dir, f"litellm_log_{RUN_ID}.json")
        with open(litellm_file, "w") as f:
            json.dump(global_serializable, f, indent=2)
        logger.info(f"Flushed LiteLLM logs to {litellm_file}")

# Singleton instance
central_logger = CentralLogger()

# Register flush_logs to run at program exit
atexit.register(central_logger.flush_logs)