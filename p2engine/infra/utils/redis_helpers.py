from __future__ import annotations

import json
from typing import Any, Dict


REDIS_SAFE_TYPES = (str, bytes, int, float)


def serialise_for_redis(d: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert *d* so every value is acceptable for redis-py's XADD / HSET helpers.

    ─ Accepted unchanged ─
      • str / bytes / int / float

    ─ Encoded as JSON ─
      • dict / list

    ─ Fallback ─
      • everything else → str(v)
    """
    out: Dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, REDIS_SAFE_TYPES):
            out[k] = v
        elif isinstance(v, (dict, list)):
            out[k] = json.dumps(v, separators=(",", ":"), ensure_ascii=False)
        else:
            out[k] = str(v)
    return out
