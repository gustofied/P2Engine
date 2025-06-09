from __future__ import annotations

import multiprocessing as _mp
import os
import sys
import threading
from typing import Final

from infra.logging.logging_config import logger

# ─────────────────────────────────────────────────────────────────────────────
# Quiet-by-default LiteLLM logging
#   • honour operator-supplied value
#   • otherwise default to “error”
#   • MUST be set before the first “import litellm” anywhere in the process
# ─────────────────────────────────────────────────────────────────────────────
os.environ.setdefault("LITELLM_LOG_LEVEL", "error")

os.environ.setdefault("LITELLM_DISABLE_CACHE_UPDATE", "true")
os.environ.setdefault("LITELLM_NO_GITHUB_MODEL_PRICES", "true")

_global_init_lock: Final[threading.Lock] = threading.Lock()
_global_init_done: bool = False


def _inside_celery_runtime() -> bool:
    if os.getenv("INSIDE_CELERY"):
        return True
    if os.getenv("CELERY_WORKER") or os.getenv("CELERY_WORKER_RUNNING"):
        return True
    if any("celery" in arg for arg in sys.argv) and any(x in sys.argv for x in ("worker", "beat", "multi")):
        return True
    return _mp.current_process().name.startswith("ForkPoolWorker-")


def _ensure_evaluators_loaded() -> None:
    from infra.evals.loader import load_all as _load_evaluators

    _load_evaluators()


def run_once_global_init() -> None:
    global _global_init_done

    if _inside_celery_runtime():
        logger.info("Running inside Celery – skipping heavy global_init and " "falling back to minimal worker bootstrap")
        minimal_worker_init()
        return

    with _global_init_lock:
        if _global_init_done:
            logger.debug("Global initialization already completed – skipping")
            return
        _global_init_done = True

    _ensure_evaluators_loaded()

    from infra.runtime import global_init

    logger.info("Starting single-pass global initialization…")
    global_init()
    logger.info("Global initialization finished")


def minimal_worker_init() -> None:
    from tools import load_tools

    _ensure_evaluators_loaded()
    logger.info("Performing minimal initialization for Celery worker")
    load_tools()
