import json
import time

from infra.clients.redis_client import get_redis


def log_interaction_event(
    conversation_id: str,
    event_type: str,
    agent_id: str,
    correlation_id: str | None,
    payload: dict,
):
    redis_client = get_redis()
    key = f"trace:{conversation_id}"
    entry = {
        "ts": time.time(),
        "agent": agent_id,
        "event": event_type,
        "correlation_id": correlation_id,
        "payload": payload,
    }
    redis_client.rpush(key, json.dumps(entry))
