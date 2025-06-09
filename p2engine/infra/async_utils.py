"""Async‑utils – now self‑healing when the shared event‑loop is missing or dead."""

from __future__ import annotations

import asyncio
import logging
import sys
from threading import Thread

from infra.logging.logging_config import LoggerStream, litellm_logger, logger

# A single shared loop reference for the whole process.
# *Every* Celery worker will overwrite this with its own running loop.
loop: asyncio.AbstractEventLoop | None = None


def set_event_loop(new_loop: asyncio.AbstractEventLoop) -> None:
    """Install *new_loop* as the global event‑loop reference."""
    global loop
    if loop is not None and loop.is_running():
        logger.warning("Overwriting an already running event loop")
    loop = new_loop
    logger.debug("Event loop set in async_utils")


def _bootstrap_background_loop() -> None:
    """Spawn a thread that runs :pyfunc:`start_event_loop`."""
    t = Thread(target=start_event_loop, daemon=True, name="AsyncLoop")
    t.start()
    # give the loop a moment so callers can schedule coroutines right away
    t.join(0.1)


def start_event_loop() -> None:
    """Create a brand‑new loop and run it forever in the current thread."""
    global loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # pipe stdout / stderr into litellm to avoid interleaving in worker logs
    sys.stdout = LoggerStream(litellm_logger, logging.DEBUG)
    sys.stderr = LoggerStream(litellm_logger, logging.ERROR)

    logger.debug("Event loop started in thread with stdout redirection")
    loop.run_forever()


# --------------------------------------------------------------------------- #
# Public helpers
# --------------------------------------------------------------------------- #


def run_async(coro):
    """Run *coro* on the background loop and return its result synchronously.

    If no loop exists **or** the referenced loop has stopped (after a fork, for
    example) we transparently start a new one so callers never block forever.
    """
    global loop

    if loop is None or not loop.is_running():
        logger.warning("Creating new event loop on demand (missing or stopped)")
        set_event_loop(asyncio.new_event_loop())
        _bootstrap_background_loop()

    try:
        fut = asyncio.run_coroutine_threadsafe(coro, loop)
        return fut.result()
    except Exception as exc:  # pragma: no cover – surfaces the real error
        logger.error("run_async failed: %s", exc, exc_info=True)
        raise


def run_async_fire_and_forget(coro):
    """Schedule *coro* on the loop without waiting for the result."""
    global loop

    if loop is None or not loop.is_running():
        logger.warning("Creating new event loop on demand (missing or stopped)")
        set_event_loop(asyncio.new_event_loop())
        _bootstrap_background_loop()

    asyncio.run_coroutine_threadsafe(coro, loop)
