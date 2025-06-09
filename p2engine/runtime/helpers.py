from __future__ import annotations

import hashlib
import json
import logging
import time
from typing import TYPE_CHECKING, List, Union

from orchestrator.interactions.serializers import encode
from orchestrator.interactions.states.assistant_message import (
    AssistantMessageState,
)
from orchestrator.interactions.states.finished import FinishedState
from orchestrator.interactions.states.tool_call import ToolCallState
from orchestrator.interactions.states.user_message import UserMessageState
from orchestrator.interactions.states.waiting import WaitingState
from orchestrator.schemas.schemas import FunctionCallSchema, ReplySchema
from runtime.constants import TOOL_TIMEOUT_SEC
from runtime.effects import BaseEffect, CallTool, PublishSystemReply

if TYPE_CHECKING:  # pragma: no cover
    from orchestrator.interactions.stack import InteractionStack

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
#  Helper predicates to decide whether the *root* agent should be auto-finished
# ─────────────────────────────────────────────────────────────────────────────
def _is_cli_session(r, cid: str) -> bool:
    """True if this conversation is an interactive CLI chat."""
    return bool(r.get(f"conversation:{cid}:is_cli"))


def _is_rollout_session(r, cid: str) -> bool:
    """True if this conversation was spawned by a roll-out task."""
    return r.get(f"conversation:{cid}:mode") == "rollout"


# ─────────────────────────────────────────────────────────────────────────────
#  Mark the current branch finished (used by many runtime handlers)
# ─────────────────────────────────────────────────────────────────────────────
def mark_finished(stack: "InteractionStack") -> None:
    root_branch = stack.get_parent_agent_id() is None

    # keep the root agent open for live CLI sessions
    if root_branch and _is_cli_session(stack.redis, stack.cid):
        return

    # otherwise (roll-out root or any child branch) finish if not already done
    if isinstance(stack.current().state, FinishedState):
        return

    # don’t finish while we’re still waiting for a tool / agent / user input
    if any(isinstance(e.state, WaitingState) and not e.state.is_expired() for e in stack.iter_last_n(stack.length())):
        return

    stack.push(FinishedState())
    stack.redis.sadd(f"session:{stack.cid}:finished", stack.aid)


def mark_child_finished(stack: "InteractionStack") -> None:
    """
    For backwards-compat — some call-sites still use the old helper name but
    the semantics are identical to `mark_finished()` now.
    """
    mark_finished(stack)


# ─────────────────────────────────────────────────────────────────────────────
#  Utility helpers (unchanged)
# ─────────────────────────────────────────────────────────────────────────────
def _hash_tool_call(name: str, params: dict) -> str:
    blob = json.dumps({"name": name, "params": params}, sort_keys=True)
    return hashlib.sha1(blob.encode()).hexdigest()


def _inject_rollout_meta(stack: "InteractionStack", conversation_id: str, meta):
    team_id_val = stack.redis.get(f"{conversation_id}:team")
    variant_id_val = stack.redis.get(f"{conversation_id}:variant")
    if not (team_id_val or variant_id_val):
        return meta
    rollout_meta = {}
    if team_id_val:
        rollout_meta["team_id"] = team_id_val if isinstance(team_id_val, str) else team_id_val.decode()
    if variant_id_val:
        rollout_meta["variant_id"] = variant_id_val if isinstance(variant_id_val, str) else variant_id_val.decode()
    if meta is None:
        return rollout_meta
    if isinstance(meta, dict):
        meta.update(rollout_meta)
        return meta
    return {"note": meta, **rollout_meta}


def materialise_response(
    stack: "InteractionStack",
    response: Union[ReplySchema, FunctionCallSchema, None],
    conversation_id: str,
    agent_id: str,
) -> List[BaseEffect]:
    if response is None:
        logger.error({"message": "Agent returned None", "agent_id": agent_id})
        return []

    # ── plain text reply ────────────────────────────────────────────────────
    if isinstance(response, ReplySchema):
        last_entry = stack.current()
        meta = last_entry.state.meta if last_entry and isinstance(last_entry.state, UserMessageState) else None
        meta = _inject_rollout_meta(stack, conversation_id, meta)
        message = response.message.strip()
        stack.push(AssistantMessageState(content=message, meta=meta))

        is_child_branch = stack.get_parent_agent_id() is not None
        if is_child_branch:
            mark_child_finished(stack)
        else:
            mark_finished(stack)

        effects: List[BaseEffect] = []
        if not is_child_branch:
            effects.append(PublishSystemReply(conversation_id, message))
        return effects

    # ── function / tool call ────────────────────────────────────────────────
    if isinstance(response, FunctionCallSchema):
        tool_hash = _hash_tool_call(response.function_name, response.arguments)
        branch_id = stack.current_branch()

        # If we’re already waiting on *exactly* the same tool-call don’t queue twice
        top = stack.current()
        if isinstance(top.state, WaitingState):
            if top.state.correlation_id == tool_hash:
                return []
            return [
                PublishSystemReply(
                    conversation_id,
                    "Let’s finish the current action before starting another.",
                )
            ]

        # schedule the tool call
        tool_state = ToolCallState(
            id=tool_hash,
            function_name=response.function_name,
            arguments=response.arguments,
        )
        waiting_state = WaitingState(
            kind="tool",
            deadline=time.time() + TOOL_TIMEOUT_SEC,
            correlation_id=tool_hash,
        )
        stack.push(tool_state, waiting_state)

        return [
            CallTool(
                conversation_id=conversation_id,
                agent_id=agent_id,
                branch_id=branch_id,
                tool_name=response.function_name,
                parameters=response.arguments,
                tool_call_id=tool_hash,
                tool_state_env=encode(tool_state),
            )
        ]

    # ── unexpected return type ──────────────────────────────────────────────
    logger.error(
        {
            "message": "Unexpected response type",
            "agent_id": agent_id,
            "type": type(response).__name__,
        }
    )
    return []
