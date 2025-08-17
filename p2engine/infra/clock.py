import time

from infra.logging.logging_config import logger
from infra.logging.metrics import metrics

TICK_TIMEOUT_SEC = 45


def ack_tick(redis, cid: str, aid: str, tick: int):
    """
    Removes the agent/tool 'aid' from the waiting set in the current tick.
    If after removing them the set is empty, the session driver can proceed to next tick.
    """
    waiting_key = f"session:{cid}:waiting:{tick}"
    if redis.srem(waiting_key, aid):
        start_time_key = f"session:{cid}:tick:{tick}:start_time"
        start_time = float(redis.get(start_time_key) or 0)
        if start_time:
            lag = time.time() - start_time
            metrics.emit(
                "tick_lag",
                lag,
                tags={"agent_id": aid, "conversation_id": cid, "tick": tick},
            )
        logger.debug(
            {
                "message": "Agent/tool acked tick",
                "conversation_id": cid,
                "agent_or_tool": aid,
                "tick": tick,
            }
        )
