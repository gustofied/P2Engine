from __future__ import annotations

from typing import Dict, List, Optional

from infra.logging.logging_config import logger
from infra.logging.metrics import metrics

def mean_metric(values: List[float]) -> float:
    """Arithmetic mean that returns 0.0 on an empty list (no NaN)."""
    if not values:
        return 0.0
    return sum(values) / len(values)


def record_latency_ms(evaluator_id: str, ms: float, *, tags: Optional[Dict] = None) -> None:
    """
    Emit a `eval_latency` metric for dashboards and alerting.

    Called *once per individual* evaluation – even when requests are batched.
    """
    payload_tags = {"evaluator_id": evaluator_id}
    if tags:
        payload_tags.update(tags)
    metrics.emit("eval_latency", ms, tags=payload_tags)
    logger.debug(
        {
            "message": "metric_emit",
            "metric": "eval_latency",
            "value": ms,
            "tags": payload_tags,
        }
    )


__all__ = ["mean_metric", "record_latency_ms"]
