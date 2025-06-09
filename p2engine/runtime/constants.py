import os
from typing import Final

TOOL_TIMEOUT_SEC: Final = 30
MIN_AGENT_RESPONSE_SEC: Final = 30
STACK_DUPLICATE_LOOKBACK: Final = 100
MAX_STACK_LEN: Final = 2000
MAX_REFLECTIONS: Final = int(os.getenv("MAX_REFLECTIONS", "3"))
