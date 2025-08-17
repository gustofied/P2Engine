from __future__ import annotations
import json
import time
from typing import Any, Dict
import redis
from celery import Task
from infra.artifacts.bus import get_bus
from infra.evals.metrics import record_latency_ms
from infra.evals.registry import registry
from infra.logging.logging_config import logger
from runtime.tasks.celery_app import app



def _update_status(ref: str, status: str, **extra) -> None:
    """
    Patch the evaluation artefact’s header so that stream watchers
    (e.g. wait_for_eval) can see pending → running → finished transitions.
    """
    try:
        get_bus().patch_artifact(
            ref,
            updates_header={
                "meta": {"status": status},
                **extra,
            },
        )
    except Exception as exc:
        logger.error(
            {
                "message": "eval_status_patch_failed",
                "ref": ref,
                "target_status": status,
                "error": str(exc),
            },
            exc_info=True,
        )


def _maybe_get_cache(rds: redis.Redis, cache_key: str | None) -> Dict[str, Any] | None:
    if not cache_key:
        return None
    try:
        raw = rds.get(cache_key)
        return json.loads(raw) if raw else None
    except Exception:
        return None


def _maybe_set_cache(rds: redis.Redis, cache_key: str | None, ttl: int, result: Dict[str, Any]) -> None:
    if not cache_key:
        return
    try:
        rds.setex(cache_key, ttl, json.dumps(result))
    except Exception:
        pass



@app.task(
    name="runtime.tasks.evals.run_eval",
    queue="evals",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    max_retries=3,
)
def run_eval(
    self: Task,
    ref: str,
    evaluator_id: str,
    judge_version: str,
    payload: Dict[str, Any],
    _cached: bool = False,
) -> None:
    """
    Execute `evaluator_id` with the given payload, store the score/metrics
    back into the evaluation artefact referenced by *ref*, and finally mark
    the artefact as **finished** so that `wait_for_eval` can stop polling.
    """
    bus = get_bus()
    rds: redis.Redis = bus.redis


    _update_status(ref, "running")


    cache_key: str | None
    cache_ttl: int
    try:
        from infra.evals.batcher import EvaluationCoordinator

        cache_key = EvaluationCoordinator._dedupe_key(
            evaluator_id,
            judge_version,
            payload,
        )
        cache_ttl = EvaluationCoordinator._CACHE_TTL_SEC
    except Exception:
        cache_key = None
        cache_ttl = 0

    cached_result = _maybe_get_cache(rds, cache_key)
    if cached_result:
        result = cached_result
        latency_ms = result.get("latency_ms", 0.0)

        logger.debug(
            {
                "message": "eval_cache_hit",
                "ref": ref,
                "evaluator_id": evaluator_id,
                "judge_version": judge_version,
            }
        )

        record_latency_ms(evaluator_id, latency_ms)
        bus.patch_artifact(ref, updates_payload=result)


        _update_status(
            ref,
            "finished",
            score=result.get("score"),
            eval_metrics=result.get("eval_metrics", {}),
        )
        return


    evaluator = registry.get(evaluator_id, version=judge_version)
    if evaluator is None:
        _update_status(
            ref,
            "error",
            error=f"Evaluator '{evaluator_id}' (version {judge_version}) not found.",
        )
        raise RuntimeError(f"Evaluator '{evaluator_id}:{judge_version}' not registered")

    start_ns = time.perf_counter_ns()
    try:
        result: Dict[str, Any] = evaluator(**payload)
    except Exception as exc:
        _update_status(ref, "error", error=str(exc))
        raise

    latency_ms = (time.perf_counter_ns() - start_ns) / 1_000_000.0
    record_latency_ms(evaluator_id, latency_ms)


    bus.patch_artifact(ref, updates_payload=result)

    _update_status(
        ref,
        "finished",
        score=result.get("score"),
        eval_metrics=result.get("eval_metrics", {}),
    )


    try:
        hdr, payload = bus.get(ref)  
        hdr["meta"] = hdr.get("meta", {}) | {"status": "finished"}
        bus.publish(hdr, payload)
    except Exception as exc:
        logger.error(
            {
                "message": "eval_finish_publish_failed",
                "ref": ref,
                "error": str(exc),
            },
            exc_info=True,
        )

    _maybe_set_cache(rds, cache_key, cache_ttl, result)

    logger.info(
        {
            "message": "eval_completed",
            "ref": ref,
            "evaluator_id": evaluator_id,
            "judge_version": judge_version,
            "latency_ms": latency_ms,
            "score": result.get("score"),
        }
    )
