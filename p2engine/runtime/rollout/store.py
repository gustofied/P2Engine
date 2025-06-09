from __future__ import annotations

import time
from typing import Tuple

import redis


class RolloutStore:
    """
    Thin Redis wrapper for tracking roll-out progress.

    • Each roll-out lives under one key:  rollout:<rollout_id>
    • We store a tiny hash so HGET/HSET stay O(1)
    • Keys auto-expire (default 7 days) so memory cannot leak forever
    """

    _PREFIX = "rollout:"
    _DEFAULT_TTL_SEC = 7 * 24 * 60 * 60  # 7 days

    def __init__(self, r: redis.Redis):
        self._r = r

    # --------------------------------------------------------------------- #
    # lifecycle                                                             #
    # --------------------------------------------------------------------- #

    def create(self, rollout_id: str, total: int, *, ttl: int | None = None) -> None:
        """
        Initialise a new roll-out record.

        Parameters
        ----------
        rollout_id : str
            Unique id — usually f"multi:{time_ns()}"
        total : int
            Number of variants we *expect* to run.
        ttl : int | None
            Optional custom expiry-time in seconds (defaults to 7 days).
        """
        key = f"{self._PREFIX}{rollout_id}"
        self._r.hset(
            key,
            mapping={"total": total, "completed": 0, "done": 0, "created_ts": int(time.time())},
        )
        self._r.expire(key, ttl or self._DEFAULT_TTL_SEC)

    # --------------------------------------------------------------------- #
    # helpers                                                               #
    # --------------------------------------------------------------------- #

    def incr_completed(self, rollout_id: str) -> int:
        """Atomically bump the completed counter and return the new value."""
        return int(self._r.hincrby(f"{self._PREFIX}{rollout_id}", "completed", 1) or 0)

    def progress(self, rollout_id: str) -> Tuple[int, int]:
        """Return (completed, total)."""
        completed, total = self._r.hmget(f"{self._PREFIX}{rollout_id}", "completed", "total")
        return int(completed or 0), int(total or 0)

    def is_done(self, rollout_id: str) -> bool:
        """True once `mark_done()` flipped the bit."""
        raw = self._r.hget(f"{self._PREFIX}{rollout_id}", "done")
        return bool(int(raw or 0))

    def mark_done(self, rollout_id: str) -> None:
        """Flag the roll-out as finished (does *not* touch TTL)."""
        self._r.hset(f"{self._PREFIX}{rollout_id}", "done", 1)

    def set_group_id(self, rollout_id: str, group_id: str) -> None:
        """Attach an arbitrary group/experiment id."""
        self._r.hset(f"{self._PREFIX}{rollout_id}", "group_id", group_id)
