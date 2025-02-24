import os
import json
import datetime
import atexit
import logging
from custom_logging.litellm_logger import my_custom_logging_fn

# Set up simple_logger
simple_logger = logging.getLogger("SimpleLogger")
simple_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(message)s'))
simple_logger.addHandler(handler)

class CentralLogger:
    def __init__(self):
        self.scenario_logs = []
        self.interaction_logs = []
        self.current_system_start_time = None

    def log_system_start(self, system_name, entities, problem, goal):
        """Start logging a system with problem and goal"""
        self.current_system_start_time = datetime.datetime.now()
        entity_data = {
            entity.id: {
                "type": entity.entity_type,
                "name": entity.name,
                "components": {k: v.__dict__ for k, v in entity.components.items()}
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
            "evaluation": None
        }
        self.scenario_logs.append(system_log)
        simple_logger.info(f"System '{system_name}' started with goal: {goal}")

    def log_interaction(self, sender, receiver, message):
        """Log interactions within the system"""
        interaction = {
            "from": sender,
            "to": receiver,
            "message": message,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.interaction_logs.append(interaction)
        if self.scenario_logs:
            self.scenario_logs[-1]["interactions"].append(interaction)
        simple_logger.info(f"Interaction: {sender} -> {receiver}: {message}")

    def log_litellm_event(self, model_call_dict):
        """Log LiteLLM events"""
        my_custom_logging_fn(model_call_dict)
        simple_logger.info(f"LiteLLM event logged: {model_call_dict.get('model', 'unknown')}")

    def log_system_end(self, result, evaluation):
        """Finalize the system log with result, evaluation, and time spent"""
        if not self.scenario_logs or not self.current_system_start_time:
            simple_logger.warning("No active system to end")
            return
        end_time = datetime.datetime.now()
        time_spent = (end_time - self.current_system_start_time).total_seconds()
        self.scenario_logs[-1]["time_spent"] = time_spent
        self.scenario_logs[-1]["result"] = result
        self.scenario_logs[-1]["evaluation"] = evaluation
        simple_logger.info(f"System ended. Time spent: {time_spent}s, Result: {result}")

    def flush_logs(self):
        """Flush logs to JSON files"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        system_file = os.path.join(log_dir, f"system_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(system_file, "w") as f:
            json.dump(self.scenario_logs, f, indent=2)
        print(f"Flushed system logs to {system_file}")

        interaction_file = os.path.join(log_dir, f"interaction_log_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
        with open(interaction_file, "w") as f:
            json.dump(self.interaction_logs, f, indent=2)
        print(f"Flushed interaction logs to {interaction_file}")

# Global logger instance with automatic flush at exit
central_logger = CentralLogger()
atexit.register(central_logger.flush_logs)