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

class CentralLogger:
    def __init__(self):
        """Initialize the logger with empty log lists and no active system start time."""
        self.scenario_logs = []  # List to store all scenario logs
        self.interaction_logs = []  # List to store all interaction logs
        self.current_system_start_time = None  # Tracks the start time of the current system

    def log_system_start(self, system_name: str, entities: dict, problem: str, goal: str, expected_result: str = None) -> None:
        """Log the start of a system with its details."""
        self.current_system_start_time = datetime.datetime.now()
        # Format entity data for logging
        entity_data = {
            entity_id: {
                "type": entity.entity_type,
                "name": entity.name,
                "components": {k: vars(v) for k, v in entity.components.items()}
            } for entity_id, entity in entities.items()
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
            "metadata": metadata if metadata else {}
        }
        self.interaction_logs.append(interaction)
        if self.scenario_logs:
            self.scenario_logs[-1]["interactions"].append(interaction)
        logger.info(f"Interaction: {sender} -> {receiver}: {message[:50]}...")

    def log_litellm_event(self, model_call_dict: dict) -> None:
        """Log a LiteLLM event (assumes a custom logging function exists)."""
        # Placeholder for my_custom_logging_fn; replace with actual implementation if needed
        logger.info(f"LiteLLM event logged: {model_call_dict.get('model', 'unknown')}")

    def log_system_end(self, result: str, evaluation: dict, reward: int, all_agents: dict) -> None:
        """Log the end of a system with its results."""
        if not self.scenario_logs or not self.current_system_start_time:
            logger.warning("No active system to end")
            return
        end_time = datetime.datetime.now()
        time_spent = (end_time - self.current_system_start_time).total_seconds()
        self.scenario_logs[-1].update({
            "time_spent": time_spent,
            "result": result,
            "evaluation": evaluation,
            "reward": reward,
            "entities": all_agents  # Update entities with all agents involved
        })
        logger.info(f"System ended. Time spent: {time_spent}s, Result: {result[:50]}..., Reward: {reward}")

    def get_logs(self):
        """Return the most recent scenario log."""
        if not self.scenario_logs:
            logger.warning("No scenario logs available to return")
            return {}
        return self.scenario_logs[-1]

    def flush_logs(self) -> None:
        """Write all logs to JSON files in the 'logs' directory."""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # Helper function to ensure JSON serializability
        def make_json_serializable(data):
            if isinstance(data, (list, tuple)):
                return [make_json_serializable(item) for item in data]
            if isinstance(data, dict):
                return {k: make_json_serializable(v) for k, v in data.items()}
            if isinstance(data, (str, int, float, bool)) or data is None:
                return data
            return str(data)

        # Flush scenario logs
        scenario_serializable = make_json_serializable(self.scenario_logs)
        system_file = os.path.join(log_dir, f"system_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(system_file, "w") as f:
            json.dump(scenario_serializable, f, indent=2)
        logger.info(f"Flushed system logs to {system_file}")

        # Flush interaction logs
        interaction_serializable = make_json_serializable(self.interaction_logs)
        interaction_file = os.path.join(log_dir, f"interaction_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(interaction_file, "w") as f:
            json.dump(interaction_serializable, f, indent=2)
        logger.info(f"Flushed interaction logs to {interaction_file}")

# Create a singleton instance
central_logger = CentralLogger()