import os
import json
import datetime
import atexit
import logging
from custom_logging.litellm_logger import my_custom_logging_fn, make_json_serializable

logger = logging.getLogger("CentralLogger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

class CentralLogger:
    def __init__(self):
        self.scenario_logs = []
        self.interaction_logs = []
        self.current_system_start_time = None

    def log_system_start(self, system_name: str, entities: dict, problem: str, goal: str) -> None:
        self.current_system_start_time = datetime.datetime.now()
        entity_data = {
            entity.id: {
                "type": entity.entity_type,
                "name": entity.name,
                # Use vars() to capture the component state.
                "components": {k: vars(v) for k, v in entity.components.items()}
            } for entity in entities.values()
        }
        system_log = {
            "system_name": system_name,
            "start_time": self.current_system_start_time.isoformat(),
            "entities": entity_data,
            "problem": problem,
            "goal": goal,
            "interactions": [],
            "time_spent": None,
            "result": None,
            "evaluation": None,
            "reward": None
        }
        self.scenario_logs.append(system_log)
        logger.info(f"System '{system_name}' started with goal: {goal}")

    def log_interaction(self, sender: str, receiver: str, message: str) -> None:
        interaction = {
            "from": sender,
            "to": receiver,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.interaction_logs.append(interaction)
        if self.scenario_logs:
            self.scenario_logs[-1]["interactions"].append(interaction)
        logger.info(f"Interaction: {sender} -> {receiver}: {message}")

    def log_litellm_event(self, model_call_dict: dict) -> None:
        my_custom_logging_fn(model_call_dict)
        logger.info(f"LiteLLM event logged: {model_call_dict.get('model', 'unknown')}")

    def log_system_end(self, result: str, evaluation: dict, reward: int) -> None:
        if not self.scenario_logs or not self.current_system_start_time:
            logger.warning("No active system to end")
            return
        end_time = datetime.datetime.now()
        time_spent = (end_time - self.current_system_start_time).total_seconds()
        self.scenario_logs[-1]["time_spent"] = time_spent
        self.scenario_logs[-1]["result"] = result
        self.scenario_logs[-1]["evaluation"] = evaluation
        self.scenario_logs[-1]["reward"] = reward
        logger.info(f"System ended. Time spent: {time_spent}s, Result: {result}, Reward: {reward}")

    def flush_logs(self) -> None:
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        # Use the custom serializer to handle non-serializable objects.
        scenario_serializable = make_json_serializable(self.scenario_logs)
        system_file = os.path.join(log_dir, f"system_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(system_file, "w") as f:
            json.dump(scenario_serializable, f, indent=2)
        logger.info(f"Flushed system logs to {system_file}")

        interaction_serializable = make_json_serializable(self.interaction_logs)
        interaction_file = os.path.join(log_dir, f"interaction_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(interaction_file, "w") as f:
            json.dump(interaction_serializable, f, indent=2)
        logger.info(f"Flushed interaction logs to {interaction_file}")

central_logger = CentralLogger()
atexit.register(central_logger.flush_logs)
