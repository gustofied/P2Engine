"""
Utility for loading JSON-style rubric Jinja templates.

Adds:
  • in-process LRU cache               → avoids disk churn in big sweeps
  • name whitelist / path sanitisation → blocks `../../../` escapades
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

_RUBRIC_DIR = Path(__file__).parent / "rubrics"

# single regex – cheap and explicit
_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_\-]+$")  # e.g. "friendly_ping", "weather-accuracy"


class RubricNotFound(KeyError):
    """Raised when the requested rubric id does not map to a template on disk."""


@lru_cache(maxsize=256)
def get_rubric_text(rubric_id: str) -> str:
    """
    Fetch the Jinja template text for a rubric id.

    Guard-rails
    -----------
    • id must match ``^[A-Za-z0-9_\\-]+$``
    • template must live exactly at `<repo>/infra/evals/rubrics/<id>.jinja`
    • result cached via functools.lru_cache (256-entry default)
    """
    if not _SAFE_NAME_RE.fullmatch(rubric_id):
        raise ValueError(f"Illegal rubric id '{rubric_id}'. Only letters, digits, '_', '-' allowed.")

    path = _RUBRIC_DIR / f"{rubric_id}.jinja"
    if not path.is_file():
        raise RubricNotFound(f"Unknown rubric '{rubric_id}' " f"(expected template at {_RUBRIC_DIR / (rubric_id + '.jinja')})")

    # Encoding chosen to match upstream loader logic (UTF-8)
    return path.read_text(encoding="utf-8")
