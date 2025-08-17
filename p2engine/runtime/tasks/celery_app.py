from __future__ import annotations

import logging
import multiprocessing as _mp
import os
import sys
from pathlib import Path

from celery import Celery
from celery.signals import worker_init, worker_process_init
from kombu import Queue

import infra.async_utils as async_utils
from infra.artifacts.bus import ArtifactBus
from infra.bootstrap import minimal_worker_init
from infra.config import BASE_DIR
from infra.config_loader import settings
from infra.logging.logging_config import LoggerStream, litellm_logger, logger
from services.services import ServiceContainer

os.environ.setdefault("LITELLM_LOG_LEVEL", "error")


def _redirect_litellm_output() -> None:
    sys.stdout = LoggerStream(litellm_logger, logging.DEBUG)
    sys.stderr = LoggerStream(litellm_logger, logging.ERROR)


os.environ.setdefault("INSIDE_CELERY", "1")

app = Celery(
    "p2engine",
    broker=f"redis://{settings().redis.host}:{settings().redis.port}/{settings().redis.db}",
    backend=f"redis://{settings().redis.host}:{settings().redis.port}/{settings().redis.db}",
)
app.conf.broker_connection_retry_on_startup = True

ROLL_Q = "rollouts"
TOOLS_Q = "tools"
EVALS_Q = "evals"

app.conf.task_queues = (
    Queue("ticks"),
    Queue(ROLL_Q),
    Queue(TOOLS_Q),
    Queue(EVALS_Q),
)
app.conf.task_default_queue = "ticks"
app.conf.task_routes = {
    "runtime.tasks.tasks.process_session_tick": {"queue": "ticks"},
    "runtime.tasks.tasks.execute_tool": {"queue": TOOLS_Q},
    "runtime.tasks.evals.run_eval": {"queue": EVALS_Q},
    "runtime.tasks.delegate_bridge.bubble_up_delegate": {"queue": "ticks"},
    "runtime.tasks.evals_flush.flush_batch": {"queue": "ticks"},
    "runtime.tasks.rollout_tasks.run_variant": {"queue": ROLL_Q},
    "celery.chord_unlock": {"queue": "ticks"},
}
app.conf.worker_prefetch_multiplier = 1
app.autodiscover_tasks(["runtime.tasks"], force=True)

logger.info("Celery queues configured: ticks, rollouts, tools, evals (chord unlock→ticks)")


@worker_init.connect
def _worker_parent_init(**_) -> None:
    _redirect_litellm_output()
    minimal_worker_init()
    from infra.evals.loader import load_all as _load_evaluators

    _load_evaluators()
    from runtime.task_runner import get_task_context

    get_task_context()


@worker_process_init.connect
def _worker_child_init(**_) -> None:
    minimal_worker_init()
    async_utils.loop = None
    async_utils._bootstrap_background_loop()
    sys.stdout = LoggerStream(litellm_logger, logging.DEBUG)
    sys.stderr = LoggerStream(litellm_logger, logging.ERROR)

    container = ServiceContainer()
    ArtifactBus.get_instance(
        redis_client=container.get_redis_client(),
        base_dir=Path(os.getenv("LOG_DIR", BASE_DIR)),
    )

    proc_name = _mp.current_process().name
    logger.debug("%s fully initialised", proc_name)
