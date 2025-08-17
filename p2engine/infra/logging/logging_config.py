from __future__ import annotations

import atexit
import json
import logging
import os
import queue
import re
import sys
from contextlib import contextmanager
from datetime import datetime
from io import StringIO
from logging.handlers import QueueHandler, QueueListener, TimedRotatingFileHandler
from typing import Any

from infra.config import BASE_DIR
from infra.config_loader import settings


class _SingleInfoFilter(logging.Filter):
    """
    Let the first occurrence of certain *chatty* INFO lines through,
    then drop the rest. One set per process – enough to keep main.log
    scannable even when lots of forks spin up.
    """

    _SEEN: set[str] = set()
    _PATTERNS = (
        "Imported tool module:",
        "Registered tools:",
        "Celery queues configured:",
        "LLMClient initialized",
        "ServiceContainer initialised",
        "ServiceContainer initialized",
        "Agent registered",
        "already registered",
    )

    def filter(self, record: logging.LogRecord) -> bool:
        if record.levelno != logging.INFO:
            return True
        msg = str(record.getMessage())
        if not any(p in msg for p in self._PATTERNS):
            return True
        if msg in self._SEEN:
            return False
        self._SEEN.add(msg)
        return True



STANDARD_LOG_RECORD_ATTRIBUTES = {
    "args",
    "asctime",
    "created",
    "exc_info",
    "exc_text",
    "filename",
    "funcName",
    "levelname",
    "levelno",
    "lineno",
    "module",
    "msecs",
    "msg",
    "name",
    "pathname",
    "process",
    "processName",
    "relativeCreated",
    "stack_info",
    "thread",
    "threadName",
}


class ConsoleCleanFilter(logging.Filter):
    _ANSI_RE = re.compile(r"\x1B\[[0-9;]*[mK]")

    def __init__(self) -> None:
        super().__init__()
        self._skip = False

    def filter(self, record: logging.LogRecord) -> bool:
        message = record.getMessage()
        if message.startswith(
            (
                "POST Request Sent from LiteLLM:",
                "LiteLLM model call details:",
            )
        ):
            self._skip = True
            return False
        if message.startswith("Filtered callbacks:"):
            self._skip = False
            return False
        if self._skip:
            return False

        if not isinstance(record.msg, (str, bytes, bytearray)):
            try:
                record.msg = json.dumps(record.msg, default=str)
            except Exception:
                record.msg = str(record.msg)
        if isinstance(record.msg, (bytes, bytearray)):
            record.msg = record.msg.decode(errors="replace")
        record.msg = self._ANSI_RE.sub("", record.msg)
        return True


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        doc: dict[str, Any] = {
            "timestamp": datetime.utcfromtimestamp(record.created).isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "funcName": record.funcName,
            "lineno": record.lineno,
        }
        for k, v in record.__dict__.items():
            if k not in STANDARD_LOG_RECORD_ATTRIBUTES and not k.startswith("_") and not callable(v):
                doc[k] = v
        return json.dumps(doc, default=str)



LOG_DIR = os.getenv("LOG_DIR", os.path.join(BASE_DIR, settings().logging.log_dir))
os.makedirs(LOG_DIR, exist_ok=True)


def _log_path(name: str) -> str:
    return os.path.join(LOG_DIR, name)


MAIN_LOG = _log_path("main.log")
LITELLM_DEBUG_LOG = _log_path("litellm_debug.log")

log_queue: queue.Queue[logging.LogRecord] = queue.Queue(-1)
queue_handler = QueueHandler(log_queue)

file_handler = TimedRotatingFileHandler(
    MAIN_LOG,
    when="midnight",
    backupCount=3,
    encoding="utf-8",
)
file_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))

console_clean = ConsoleCleanFilter()
dup_suppress = _SingleInfoFilter()

queue_handler.addFilter(dup_suppress)
file_handler.addFilter(console_clean)
file_handler.addFilter(dup_suppress)

queue_listener = QueueListener(log_queue, file_handler)
queue_listener.start()
atexit.register(queue_listener.stop)

_LOG_TO_CONSOLE = os.getenv("LOG_TO_CONSOLE", "0").lower() not in {"0", "false", "no"}
console_handler: logging.Handler | None = None
if _LOG_TO_CONSOLE:
    try:
        from rich.logging import RichHandler  # type: ignore

        console_handler = RichHandler(rich_tracebacks=True)
    except Exception:
        console_handler = logging.StreamHandler(sys.stdout)

    console_handler.setFormatter(logging.Formatter("%(message)s"))
    console_handler.setLevel(logging.INFO)
    console_handler.addFilter(console_clean)
    console_handler.addFilter(dup_suppress)

log_level = getattr(logging, os.getenv("LOG_LEVEL", "INFO").upper(), logging.INFO)
logger = logging.getLogger(__name__)
logger.setLevel(log_level)
logger.handlers = [queue_handler]
if console_handler is not None:
    logger.handlers.append(console_handler)
logger.propagate = False


_debug_file_handler = TimedRotatingFileHandler(
    LITELLM_DEBUG_LOG,
    when="midnight",
    backupCount=5,
    encoding="utf-8",
)
_debug_file_handler.setLevel(logging.DEBUG)
_debug_file_handler.setFormatter(logging.Formatter("%(message)s"))

_llm_level = getattr(logging, os.getenv("LITELLM_LOG_LEVEL", "ERROR").upper(), logging.ERROR)

litellm_logger = logging.getLogger("litellm")
litellm_logger.setLevel(_llm_level)
litellm_logger.addHandler(_debug_file_handler)
litellm_logger.propagate = False  

litellm_upper_logger = logging.getLogger("LiteLLM")
litellm_upper_logger.setLevel(_llm_level)
litellm_upper_logger.addHandler(_debug_file_handler)
litellm_upper_logger.propagate = False



@contextmanager
def redirect_stdout_to_logger(_logger: logging.Logger, level: int = logging.DEBUG):
    original_stdout = sys.stdout
    buffer = StringIO()
    sys.stdout = buffer
    try:
        yield
    finally:
        sys.stdout = original_stdout
        for line in buffer.getvalue().splitlines():
            if line.strip():
                _logger.log(level, line.strip())


class _LoggerStream:
    """
    Wraps stdout / stderr and forwards every complete line to a logger.

    Added *isatty()* and *fileno()* shims so libraries that inspect
    sys.stderr / sys.stdout during start-up (Celery, click, rich, …)
    don’t crash when we redirect the streams early.
    """

    def __init__(self, _logger: logging.Logger, level: int = logging.DEBUG):
        self._logger = _logger
        self._level = level
        self._buffer: str = ""

    def write(self, msg: str) -> None:
        if not msg:
            return
        self._buffer += msg
        while "\n" in self._buffer:
            line, self._buffer = self._buffer.split("\n", 1)
            if line.strip():
                self._logger.log(self._level, line.strip())

    def flush(self) -> None:
        if self._buffer.strip():
            self._logger.log(self._level, self._buffer.strip())
            self._buffer = ""


    def isatty(self) -> bool:  # pylint: disable=invalid-name
        return False

    def fileno(self) -> int:  # type: ignore[override]
        return 0


LoggerStream = _LoggerStream


def _make_serialisable(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {k: _make_serialisable(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_make_serialisable(i) for i in obj]
    if isinstance(obj, (str, int, float, bool, type(None))):
        return obj
    return str(obj)


def litellm_logging_fn(model_call_dict: dict[str, Any]) -> None:
    safe = model_call_dict.copy()
    safe.pop("api_key", None)
    safe.pop("logger_fn", None)
    litellm_logger.debug("LiteLLM model call details: %s", json.dumps(_make_serialisable(safe)))


__all__ = [
    "redirect_stdout_to_logger",
    "litellm_logger",
    "litellm_logging_fn",
    "LoggerStream",
]
