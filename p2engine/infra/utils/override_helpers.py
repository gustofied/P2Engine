import json
from typing import Any, Dict

import redis

from infra.logging.logging_config import logger


def write_override(redis_client: redis.Redis, aid: str, cid: str, patch: Dict[str, Any]) -> bool:
    """
    Write an override patch to Redis for the given agent and conversation.

    :param redis_client: Redis client instance
    :param aid: Agent ID
    :param cid: Conversation ID
    :param patch: Dictionary containing the override changes
    :return: True if the write was successful, False if aborted due to lock
    """
    override_key = f"agent:{aid}:{cid}:override"
    current_override_str = redis_client.get(override_key)

    if current_override_str:
        current_override = json.loads(current_override_str)
    else:
        current_override = {}

    if current_override.get("lock", False) and any(k != "lock" for k in patch.keys()):
        logger.debug(f"Override locked for {aid} in {cid}, skipping patch: {patch}")
        return False

    for key, value in patch.items():
        if value is None:
            current_override.pop(key, None)
        else:
            current_override[key] = value

    redis_client.set(override_key, json.dumps(current_override), ex=604800)
    logger.info(f"Override updated for {aid} in {cid}: {current_override}")
    return True
