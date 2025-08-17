from __future__ import annotations

import json
import os
from hashlib import sha1
from typing import Dict

import redis
from celery import Celery

from infra.logging.logging_config import logger

__all__ = ["EvaluationCoordinator"]


class EvaluationCoordinator:
    """
    Replacement for the old EvaluationBatcher.

    • Directly enqueues the `run_eval` Celery task (no pending-list + timer hop)
    • Performs a tiny de-duplication window so identical requests in a burst
      share the same cached result.  This is *not* persistence-level caching –
      just enough to collapse accidental duplicates.
    """

    _CACHE_TTL_SEC = 60 * 60 * 24  
    _DEDUP_TTL_SEC = 5  

    def __init__(self, redis_client: redis.Redis, celery_app: Celery):
        self.r = redis_client
        self.app = celery_app


    def _dedupe_key(self, evaluator_id: str, judge_version: str, payload: Dict) -> str:
        blob = json.dumps(
            {"evaluator_id": evaluator_id, "judge_version": judge_version, "payload": payload}, sort_keys=True, separators=(",", ":")
        )
        return f"eval-dedupe:{sha1(blob.encode()).hexdigest()}"



    def schedule(self, ref: str, evaluator_id: str, judge_version: str, payload: Dict) -> None:
        """
        Put a *single* `run_eval` task on the queue – unless the same combination
        of evaluator/version/payload has been enqueued in the last few seconds.
        """
        dkey = self._dedupe_key(evaluator_id, judge_version, payload)

        if not self.r.set(dkey, "1", ex=self._DEDUP_TTL_SEC, nx=True):
            logger.debug({"message": "eval_dedup_hit", "ref": ref})
            return

        self.app.send_task(
            "runtime.tasks.evals.run_eval",
            args=[ref, evaluator_id, judge_version, payload, False],
            queue="evals",
            priority=6,  
        )

        logger.debug({"message": "eval_enqueued", "ref": ref, "evaluator": evaluator_id, "version": judge_version})
