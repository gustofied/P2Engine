# tools/delegate_tool.py
from __future__ import annotations

from typing import Any, Optional

from pydantic import BaseModel, ConfigDict

from agents.decorators import function_tool
from infra.logging.logging_config import logger


class DelegateInput(BaseModel):
    agent_id: str
    message: str

    # allow extra keys so users can pass arbitrary metadata
    model_config = ConfigDict(extra="allow")


@function_tool(
    name="delegate",
    description=("Spawn (or wake) another agent **in the same conversation** and ask it " "to handle a sub-task."),
    input_schema=DelegateInput,
    post_effects=["agent_call"],  # ⬅️  agent_call post-effect will do the heavy lifting
    requires_context=True,
    side_effect_free=True,
)
def delegate(
    *,
    agent_id: str,
    message: str,
    conversation_id: str,
    redis_client: Optional[Any] = None,  # kept for signature-compatibility
    **_: Any,
):
    """
    Light-weight delegation tool.

    It *does not* touch Redis or any stacks directly.  Instead it simply tells
    the runtime: “Please delegate to `agent_id` with `message`.”  The builtin
    `agent_call` post-effect will:

    1. Push an `AgentCallState` + `WaitingState` to the *parent* stack.
    2. Schedule a `PushToAgent` effect, which puts the real UserMessage on the
       child’s stack (stripping any synthetic seed).
    3. Wake the session tick so the scheduler can run the child.

    Returning a tiny payload keeps this tool truly *side-effect free* and lets
    all timeout / dedup / metrics / auto-evaluation logic remain intact.
    """
    logger.info(
        {
            "message": "delegate_tool invoked",
            "conversation_id": conversation_id,
            "child_agent": agent_id,
        }
    )

    # No direct Redis manipulation here!
    return {"status": "queued", "child": agent_id}
