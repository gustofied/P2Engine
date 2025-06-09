from __future__ import annotations

import redis


def current_episode_id(rds: redis.Redis, cid: str, aid: str, branch: str) -> str:
    """
    Return the current episode-id for a <conversation, agent, branch> tuple.
    An empty string means “no episode started yet”.
    """
    key = f"stack:{cid}:{aid}:episode:{branch}"
    raw = rds.get(key)
    if raw is None:
        return ""
    return raw if isinstance(raw, str) else raw.decode(errors="replace")
