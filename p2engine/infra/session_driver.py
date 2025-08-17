from __future__ import annotations

import time
from threading import Event
from typing import Optional, Set

import redis
import redis.exceptions  

from infra.clock import TICK_TIMEOUT_SEC
from infra.logging.logging_config import logger
from infra.logging.metrics import metrics
from runtime.tasks.celery_app import app as celery_app
from services.services import ServiceContainer



def _decode_set(raw: set[bytes] | set[str]) -> Set[str]:
    return {m.decode() if isinstance(m, bytes) else m for m in raw}


def _advance_tick(r: redis.Redis, sid: str, cur: int) -> int | str | None:
    waiting_key = f"session:{sid}:waiting:{cur}"
    agents_key = f"session:{sid}:agents"
    finished_key = f"session:{sid}:finished"
    cur_key = f"session:{sid}:tick"

    nxt = cur + 1
    wait_next = f"session:{sid}:waiting:{nxt}"
    start_next = f"session:{sid}:tick:{nxt}:start_time"

    with r.pipeline() as pipe:
        try:
            pipe.watch(waiting_key, agents_key, finished_key)

            waiting = _decode_set(pipe.smembers(waiting_key))
            finished = _decode_set(pipe.smembers(finished_key))
            still_waiting = waiting - finished
            if still_waiting:
                pipe.reset()
                return None

            for aid in _decode_set(pipe.smembers(agents_key)):
                if pipe.hget(f"agent_last_active:{sid}", aid) is None:
                    pipe.srem(agents_key, aid)

            all_agents = _decode_set(pipe.smembers(agents_key))
            live_agents = all_agents - finished
            if not live_agents:
                pipe.multi()
                pipe.delete(wait_next)
                pipe.delete(start_next)
                pipe.execute()
                return "_NO_AGENTS"

            pipe.multi()
            pipe.set(cur_key, nxt)
            pipe.delete(wait_next)
            pipe.sadd(wait_next, *live_agents)
            pipe.set(start_next, time.time())
            pipe.execute()
            return nxt
        except redis.WatchError:
            return None



def session_driver(
    poll_interval: float = 1,
    *,
    container: Optional[ServiceContainer] = None,
    stop_event: Optional[Event] = None,
) -> None:
    """Continuously advances ticks and schedules Celery tasks.

    Terminates cleanly when `stop_event` is set *or* when Redis disappears.
    """
    container = container or ServiceContainer()
    r: redis.Redis = container.get_redis_client()

    while True:
        if stop_event and stop_event.is_set():
            break

        try:
            for sid_b in r.smembers("active_sessions"):
                sid = sid_b.decode() if isinstance(sid_b, bytes) else sid_b
                cur = int(r.get(f"session:{sid}:tick") or 0)

                start_key = f"session:{sid}:tick:{cur}:start_time"
                start = float(r.get(start_key) or 0)
                if start and time.time() - start > TICK_TIMEOUT_SEC:
                    dedup_key = f"tick_timeout_logged:{sid}:{cur}"
                    if not r.get(dedup_key):
                        waiting = _decode_set(r.smembers(f"session:{sid}:waiting:{cur}"))
                        logger.error(
                            {
                                "message": "Tick timeout",
                                "conversation_id": sid,
                                "tick": cur,
                                "stalled_agents": sorted(waiting),
                            }
                        )
                        r.setex(dedup_key, 30, "1")

                res = _advance_tick(r, sid, cur)
                if res == "_NO_AGENTS":
                    r.srem("active_sessions", sid)
                    logger.info({"message": "Session finished – no live agents", "session_id": sid})
                    continue
                if res is None:
                    continue

                nxt = res
                metrics.emit("tick_started", 1, tags={"conversation_id": sid, "tick": nxt})
                celery_app.send_task(
                    "runtime.tasks.tasks.process_session_tick",
                    args=[sid],
                    queue="ticks",
                )

        except redis.exceptions.ConnectionError:
            logger.info("SessionDriver: Redis connection closed – shutting down thread")
            break

        time.sleep(poll_interval)


if __name__ == "__main__":
    session_driver()
