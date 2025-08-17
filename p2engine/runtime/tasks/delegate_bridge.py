from __future__ import annotations

import redis
from typing import TYPE_CHECKING

from infra.side_effect_executor import _settle_wait
from orchestrator.interactions.states.agent_result import AgentResultState
from orchestrator.interactions.states.tool_result import ToolResultState
from runtime.task_runner import get_task_context
from runtime.tasks.celery_app import app
from runtime.tasks.tasks import enqueue_session_tick

if TYPE_CHECKING:  
    from infra.session import get_session


@app.task(
    name="runtime.tasks.delegate_bridge.bubble_up_delegate",
    queue="ticks",
    max_retries=0,
)
def bubble_up_delegate(
    conversation_id: str,
    parent_agent_id: str,
    child_agent_id: str,
    tool_call_id: str,
    answer: str,
) -> None:
    """
    Forward a child-agent’s final answer back to the waiting parent
    interaction stack, then enqueue another session tick.

    InteractionStack and get_session are imported lazily to sidestep
    the circular-import chain seen during CLI start-up.
    """
    from orchestrator.interactions.stack import InteractionStack 
    from infra.session import get_session 

    ctx = get_task_context()
    r: redis.Redis = ctx["redis_client"]

    session = get_session(conversation_id, r)
    parent_stack = session.stack_for(parent_agent_id)

    _settle_wait(parent_stack, tool_call_id)

    parent_stack.push(
        ToolResultState(
            tool_call_id=tool_call_id,
            tool_name="delegate",
            result={
                "status": "success",
                "child": child_agent_id,
                "answer": answer,
            },
        )
    )
    parent_stack.push(
        AgentResultState(
            correlation_id=tool_call_id,
            result={
                "status": "success",
                "content": answer,
            },
        )
    )

    enqueue_session_tick(conversation_id, delay_sec=0)
