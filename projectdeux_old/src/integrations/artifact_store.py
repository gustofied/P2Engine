import json
from typing import Any
from src.redis_client import redis_client
from src.custom_logging.central_logger import central_logger

class ArtifactStore:
    def __init__(self, run_id: str = "default_run"):
        """Initialize the ArtifactStore with a Redis client and optional run_id."""
        self.redis_client = redis_client
        self.run_id = run_id

    def write(self, key: str, value: Any) -> None:
        """Write a key-value pair to Redis with run_id context."""
        try:
            serialized_value = json.dumps(value)
            self.redis_client.set(key, serialized_value)
            central_logger.log_interaction("ArtifactStore", "System", f"Wrote key '{key}' to Redis", self.run_id)
        except Exception as e:
            central_logger.log_error("ArtifactStore", e, self.run_id, context={"action": "write", "key": key})

    def read(self, key: str) -> Any:
        """Read a value from Redis by key."""
        try:
            value = self.redis_client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            central_logger.log_error("ArtifactStore", e, self.run_id, context={"action": "read", "key": key})
            return None