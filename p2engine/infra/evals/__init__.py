from __future__ import annotations

import os
from typing import TYPE_CHECKING

from infra.logging.logging_config import logger
from infra.evals.aggregate import best_branch, branch_score
from infra.evals.metrics import mean_metric
from infra.evals.registry import evaluator, registry

__all__ = [
    "evaluator",
    "registry",
    "get_evaluation_batcher",
    "mean_metric",
    "branch_score",
    "best_branch",
]


def _get_celery():
    from runtime.tasks.celery_app import app as celery_app

    return celery_app



def get_evaluation_batcher(redis_client):
    """
    Return a *singleton* instance of the new **EvaluationCoordinator**.

    Caller signature is identical to the previous `EvaluationBatcher.instance`,
    so external code does not need to change.
    """
    if not hasattr(get_evaluation_batcher, "_inst"):
        from infra.evals.batcher import EvaluationCoordinator as _Coord

        get_evaluation_batcher._inst = _Coord(redis_client, _get_celery())
        logger.info("Using new EvaluationCoordinator")

    return get_evaluation_batcher._inst
