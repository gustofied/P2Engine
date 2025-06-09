# filename: orchestrator/interactions/serializers.py
from __future__ import annotations

import base64
import gzip
import json
import os
import time
from dataclasses import asdict
from typing import Dict, Type

from infra.logging.logging_config import logger

from .states.agent_call import AgentCallState
from .states.agent_result import AgentResultState
from .states.assistant_message import AssistantMessageState

# --------------------------------------------------------------------------- #
# Concrete state classes – add new ones here and they will be auto-registered
# --------------------------------------------------------------------------- #
from .states.base import BaseState
from .states.finished import FinishedState
from .states.tool_call import ToolCallState
from .states.tool_result import ToolResultState
from .states.user_input_request import UserInputRequestState
from .states.user_message import UserMessageState
from .states.user_response import UserResponseState
from .states.waiting import WaitingState

STATE_CLASSES: Dict[str, Type[BaseState]] = {
    cls.__name__: cls
    for cls in (
        UserMessageState,
        AssistantMessageState,
        ToolCallState,
        ToolResultState,
        AgentCallState,
        AgentResultState,
        FinishedState,
        UserInputRequestState,
        UserResponseState,
        WaitingState,
    )
}

# --------------------------------------------------------------------------- #
# Encoding / decoding helpers
# --------------------------------------------------------------------------- #
_GZIP_THRESHOLD = int(os.getenv("STATE_GZIP_THRESH", "2048"))  # bytes


def _maybe_compress(raw: str) -> tuple[bool, str]:
    """
    Compress `raw` JSON string with gzip+base64 iff it exceeds `_GZIP_THRESHOLD`.
    Returns: (was_compressed, payload)
    """
    if len(raw) <= _GZIP_THRESHOLD:
        return False, raw

    compressed = gzip.compress(raw.encode())
    return True, base64.b64encode(compressed).decode()


def encode(state: BaseState) -> dict:
    """
    Turn a *State dataclass into an envelope suitable for Redis transport.

    Envelope layout:
        {
            "v": <int>              # version of the state class
            "t": <str>              # state class name, e.g. "UserMessageState"
            "ts": <float>           # server-side epoch timestamp
            "compressed": <bool>    # omitted unless True
            "data": <obj|str>       # raw dict or base64-gzip string
        }
    """
    payload = json.dumps(asdict(state), separators=(",", ":"))
    compressed, body = _maybe_compress(payload)
    envelope = {
        "v": state.__version__,  # type: ignore[attr-defined]
        "t": type(state).__name__,
        "ts": time.time(),
        "data": body,
    }
    if compressed:
        envelope["compressed"] = True
    return envelope


def decode(envelope: dict) -> BaseState:
    """
    Rebuild a *State object from its envelope.

    Handles three payload shapes:
        * compressed (gzip+base64)      -> `compressed` flag is present
        * uncompressed dict (new)       -> envelope["data"] is already a mapping
        * uncompressed JSON string      -> envelope["data"] is a str (legacy)

    If the envelope’s version is *newer* than our runtime class version, we abort.
    """
    t_name: str = envelope["t"]
    cls = STATE_CLASSES.get(t_name)
    if cls is None:
        raise ValueError(f"Unknown state type '{t_name}'")

    env_ver: int = int(envelope.get("v", 0))
    if env_ver > getattr(cls, "__version__", 1):
        raise RuntimeError(f"Cannot decode {t_name} v{env_ver}: runtime understands " f"only up to v{cls.__version__}")

    # ------------------------------------------------------------------ #
    raw = envelope["data"]

    if envelope.get("compressed"):
        # gzip + base64
        try:
            raw_json = gzip.decompress(base64.b64decode(raw)).decode()
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to decompress state '%s': %s", t_name, exc)
            raise
        data_dict = json.loads(raw_json)

    else:
        # uncompressed: could be dict (preferred) or str (legacy format)
        data_dict = json.loads(raw) if isinstance(raw, str) else raw

    # ------------------------------------------------------------------ #
    return cls(**data_dict)
