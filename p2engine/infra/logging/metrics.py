from __future__ import annotations

import json
import time
from typing import Any, Dict, Optional

import redis

from infra.logging.logging_config import logger


class _Metrics:
    def __init__(self, redis_client: Optional[redis.Redis] = None) -> None:
        self.redis = redis_client

    def emit(self, name: str, value: float | int, *, tags: Optional[Dict[str, Any]] = None) -> None:
        payload = {
            "ts": time.time(),
            "metric": name,
            "value": value,
            "tags": tags or {},
        }
        logger.info({"message": "metric_emit", **payload})
        if self.redis:
            key = f"metrics:{name}"
            self.redis.rpush(key, json.dumps(payload))
            self.redis.expire(key, 86_400)


metrics = _Metrics()
