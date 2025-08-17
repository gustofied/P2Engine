from importlib import import_module, metadata
from pathlib import Path
from types import ModuleType
from typing import List

_DISCOVERED: List[ModuleType] = []


def _import_internal() -> None:
    pkg_path = Path(__file__).parent
    for file in pkg_path.glob("*.py"):
        stem = file.stem
        if stem.startswith("_") or stem in {"__init__", "loader"}:
            continue
        mod_name = f"{__package__}.{stem}"
        _DISCOVERED.append(import_module(mod_name))


def _import_plugins() -> None:
    for ep in metadata.entry_points(group="p2engine.evaluators"):
        try:
            _DISCOVERED.append(ep.load())
        except Exception as exc:
            import logging

            logging.getLogger(__name__).warning("Failed to load evaluator plugin %s: %s", ep.name, exc)


def load_all() -> None:
    if _DISCOVERED: 
        return
    _import_internal()
    _import_plugins()


def safe_load_all() -> None:
    """
    Wrapper used by Celery worker-init hooks.

    Ensures that import errors in user-supplied evaluators fail fast and stop
    the worker from starting half-initialised (the main source of “nothing
    happens” bug reports).
    """
    try:
        load_all()
    except Exception as exc: 
        import logging

        logging.getLogger(__name__).critical("Evaluator import failed – aborting worker: %s", exc, exc_info=True)
        raise
