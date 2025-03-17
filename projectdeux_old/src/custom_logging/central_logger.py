import os
import json
import datetime
import logging
from typing import List, Optional, Dict, Any
import atexit
from src.redis_client import redis_client  # Absolute import from src package

# Set up basic logging
logger = logging.getLogger("CentralLogger")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logger.addHandler(handler)

def make_json_serializable(obj: Any, cache: set = None) -> Any:
    """Convert an object to a JSON-serializable format, handling circular references."""
    if cache is None:
        cache = set()
    
    obj_id = id(obj)
    if obj_id in cache:
        return f"<Circular reference to {type(obj).__name__}>"
    cache.add(obj_id)
    
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [make_json_serializable(item, cache) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): make_json_serializable(v, cache) for k, v in obj.items()}
    elif hasattr(obj, '__dict__'):
        return make_json_serializable(obj.__dict__, cache)
    else:
        return str(obj)

class CentralLogger:
    def __init__(self, run_id: str = None):
        """Initialize the logger with an optional run_id; default to timestamp if not provided."""
        self.run_id = run_id or datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        self.scenario_logs: List[Dict] = []
        self.interaction_logs: List[Dict] = []
        self.error_logs: List[Dict] = []
        self.simple_messages: List[Dict] = []
        self.global_log_data: Dict = {
            "run_id": self.run_id,
            "agents": {}
        }
        self.current_call_index: Dict[str, int] = {}
        self.current_system_start_time: Optional[datetime.datetime] = None

    def log_system_start(self, system_name: str, entities: Dict, problem: str, goal: str, expected_result: str = None) -> None:
        """Log the start of a system with its details."""
        self.current_system_start_time = datetime.datetime.now()
        entity_data = {entity_id: make_json_serializable(entity) for entity_id, entity in entities.items()}
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
        logger.info(f"System '{system_name}' started with goal: {goal}")

    def log_interaction(self, sender: str, receiver: str, message: str, run_id: str, metadata: Optional[Dict] = None) -> None:
        """Log an interaction to Redis and in-memory."""
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
        
        redis_key = f"logs:interactions:{run_id}"
        redis_client.rpush(redis_key, json.dumps(interaction))
        logger.info(f"Interaction: {sender} -> {receiver}: {message[:50]}...")

    def log_error(self, source: str, error: Exception, run_id: str, context: Optional[Dict] = None) -> None:
        """Log an error with context."""
        error_log = {
            "source": source,
            "error": str(error),
            "timestamp": datetime.datetime.now().isoformat(),
            "context": make_json_serializable(context) if context else {}
        }
        self.error_logs.append(error_log)
        redis_key = f"logs:errors:{run_id}"
        redis_client.rpush(redis_key, json.dumps(error_log))
        logger.error(f"Error from {source}: {str(error)}")

    def log_message(self, sender: str, receiver: str, text: str) -> None:
        """Log a simple message (replacing simple_logger functionality)."""
        log_entry = {
            "from": sender,
            "to": receiver,
            "text": text,
            "timestamp": datetime.datetime.now().isoformat()
        }
        self.simple_messages.append(log_entry)
        logger.info(f"Message: {sender} -> {receiver}: {text[:50]}...")

    def log_litellm_event(self, model_call_dict: Dict) -> None:
        """Log a LiteLLM event (replacing litellm_logger functionality)."""
        serializable_payload = make_json_serializable(model_call_dict)
        serializable_payload["logged_at"] = datetime.datetime.now().isoformat()
        event_type = serializable_payload.get("log_event_type", "unknown_event")
        category = "pre" if "pre" in event_type.lower() else "post"
        agent_id = self._extract_agent_id(serializable_payload)

        if agent_id not in self.global_log_data["agents"]:
            self.global_log_data["agents"][agent_id] = {"calls": []}

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

        logger.info(f"LiteLLM event for '{agent_id}': {model_call_dict.get('model', 'unknown')} ({category})")

    def _extract_agent_id(self, payload: Dict) -> str:
        """Extract agent ID from a LiteLLM payload."""
        agent_id = "unknown_agent"
        if "metadata" in payload and isinstance(payload["metadata"], dict):
            agent_id = payload["metadata"].get("agent_id", "unknown_agent")
        elif "litellm_params" in payload and isinstance(payload["litellm_params"], dict):
            meta = payload["litellm_params"].get("metadata", {})
            if isinstance(meta, dict):
                agent_id = meta.get("agent_id", "unknown_agent")
        return agent_id

    def log_system_end(self, result: str, evaluation: Dict, reward: int, all_agents: Dict) -> None:
        """Log the end of a system with its results."""
        if not self.scenario_logs or not self.current_system_start_time:
            logger.warning("No active system to end")
            return
        end_time = datetime.datetime.now()
        time_spent = (end_time - self.current_system_start_time).total_seconds()
        serialized_agents = make_json_serializable(all_agents)
        self.scenario_logs[-1].update({
            "time_spent": time_spent,
            "result": result,
            "evaluation": make_json_serializable(evaluation),
            "reward": reward,
            "entities": serialized_agents
        })
        logger.info(f"System ended. Time: {time_spent}s, Result: {result[:50]}..., Reward: {reward}")

    def get_logs(self) -> Dict:
        """Return the most recent scenario log."""
        return self.scenario_logs[-1] if self.scenario_logs else {}

    def get_all_logs(self) -> List[Dict]:
        """Return all scenario logs."""
        return self.scenario_logs

    def get_interaction_logs(self, run_id: str) -> List[Dict]:
        """Retrieve interaction logs from Redis."""
        redis_key = f"logs:interactions:{run_id}"
        logs = redis_client.lrange(redis_key, 0, -1)
        return [json.loads(log) for log in logs] if logs else []

    def get_error_logs(self, run_id: str) -> List[Dict]:
        """Retrieve error logs from Redis."""
        redis_key = f"logs:errors:{run_id}"
        logs = redis_client.lrange(redis_key, 0, -1)
        return [json.loads(log) for log in logs] if logs else []

    def flush_logs(self) -> None:
        """Write all logs to JSON files in the 'logs' directory."""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)

        # Scenario logs
        system_file = os.path.join(log_dir, f"system_log_{self.run_id}.json")
        with open(system_file, "w") as f:
            json.dump(make_json_serializable(self.scenario_logs), f, indent=2)

        # Interaction logs
        interaction_file = os.path.join(log_dir, f"interaction_log_{self.run_id}.json")
        with open(interaction_file, "w") as f:
            json.dump(make_json_serializable(self.interaction_logs), f, indent=2)

        # Error logs
        error_file = os.path.join(log_dir, f"error_log_{self.run_id}.json")
        with open(error_file, "w") as f:
            json.dump(make_json_serializable(self.error_logs), f, indent=2)

        # LiteLLM logs
        litellm_file = os.path.join(log_dir, f"litellm_log_{self.run_id}.json")
        with open(litellm_file, "w") as f:
            json.dump(make_json_serializable(self.global_log_data), f, indent=2)

        # Simple message logs
        simple_file = os.path.join(log_dir, f"simple_log_{self.run_id}.json")
        with open(simple_file, "w") as f:
            json.dump(make_json_serializable(self.simple_messages), f, indent=2)

        print(f"Flushed logs to {system_file}, {interaction_file}, {error_file}, {litellm_file}, {simple_file}")

central_logger = CentralLogger()
# Singleton instance will be created in main.py with run_id
# atexit.register(central_logger.flush_logs)  # Moved to main.py