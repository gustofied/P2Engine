from __future__ import annotations

import json
from typing import List, Optional, Type

from orchestrator.interactions.stack import InteractionStack
from orchestrator.interactions.states.agent_call import AgentCallState
from orchestrator.interactions.states.agent_result import AgentResultState
from orchestrator.interactions.states.assistant_message import AssistantMessageState
from orchestrator.interactions.states.finished import FinishedState
from orchestrator.interactions.states.tool_call import ToolCallState
from orchestrator.interactions.states.tool_result import ToolResultState
from orchestrator.interactions.states.user_message import UserMessageState
from orchestrator.interactions.states.user_response import UserResponseState
from orchestrator.interactions.states.waiting import WaitingState

from .render_policies import RENDER_POLICIES
from .states.base import BaseState


def _assistant_tool_call_payload(state: ToolCallState) -> dict:
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": state.id,
                "type": "function",
                "function": {
                    "name": state.function_name,
                    "arguments": json.dumps(state.arguments),
                },
            }
        ],
    }


def _tool_result_payload(state: ToolResultState) -> dict:
    payload_dict = dict(state.result)
    if state.reward is not None:
        payload_dict["reward"] = state.reward
    return {
        "role": "tool",
        "tool_call_id": state.tool_call_id,
        "name": state.tool_name,
        "content": json.dumps(payload_dict),
    }


_INTERNAL_ONLY = (
    AgentCallState,
    WaitingState,
    FinishedState,
    AgentResultState,
)


def render_for_llm(
    stack: "InteractionStack",
    last_n: int = 10,
    branch_id: Optional[str] = None,
    policy_name: str = "default",
    exclude_types: List[Type[BaseState]] = [],
) -> List[dict]:
    """
    Convert a slice of the interaction stack into ChatCompletion-style messages.
    """

    entries = list(stack.iter_last_n(last_n))
    if not entries:
        return []

    raw_states = [entry.state for entry in entries if not any(isinstance(entry.state, t) for t in exclude_types)]

    canonical: List[dict] = []
    last_assistant_had_tool_calls = False

    for state in raw_states:
        if isinstance(state, _INTERNAL_ONLY):
            continue

        # ── Hide the synthetic “__child_finished__” sentinel ────────────
        if isinstance(state, UserMessageState) and state.text == "__child_finished__":
            continue

        if isinstance(state, UserMessageState):
            canonical.append({"role": "user", "content": state.text})
            last_assistant_had_tool_calls = False

        elif isinstance(state, AssistantMessageState):
            msg = {
                "role": "assistant",
                "content": state.content or "",
                "tool_calls": state.tool_calls,
            }
            canonical.append(msg)
            last_assistant_had_tool_calls = bool(state.tool_calls)

        elif isinstance(state, ToolCallState):
            canonical.append(_assistant_tool_call_payload(state))
            last_assistant_had_tool_calls = True

        elif isinstance(state, ToolResultState):
            if last_assistant_had_tool_calls:
                canonical.append(_tool_result_payload(state))
            last_assistant_had_tool_calls = False

        elif isinstance(state, UserResponseState):
            canonical.append({"role": "user", "content": state.text})
            last_assistant_had_tool_calls = False

        else:
            raise RuntimeError(f"State {type(state).__name__} has no LLM rendering strategy. " "Add a renderer or mark it internal-only.")

    policy = RENDER_POLICIES.get(policy_name, RENDER_POLICIES["default"])
    return policy(canonical, conv_id=stack.cid)
