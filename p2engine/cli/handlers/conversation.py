from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

import typer
from rich.table import Table

from cli.utils.compat import get_redis  
from orchestrator.interactions import InteractionStack
from orchestrator.interactions.states.assistant_message import (
    AssistantMessageState,
)
from orchestrator.interactions.states.tool_call import ToolCallState
from orchestrator.interactions.states.tool_result import ToolResultState
from orchestrator.interactions.states.user_message import UserMessageState


def _resolve_conv_id(r, conv_name_or_id: str) -> str:
    cid = r.get(f"conversation:{conv_name_or_id}:id")
    if cid:
        return cid.decode() if isinstance(cid, (bytes, bytearray)) else cid
    return conv_name_or_id


def _resolve_agent_id(r, conv_name_or_id: str) -> str:
    aid = r.get(f"conversation:{conv_name_or_id}:agent_id")
    if aid:
        return aid.decode() if isinstance(aid, (bytes, bytearray)) else aid
    for key in r.keys("conversation:*:id"):
        if r.get(key) == conv_name_or_id or (isinstance(r.get(key), (bytes, bytearray)) and r.get(key).decode() == conv_name_or_id):
            conv_name = key.decode().split(":")[1] if isinstance(key, bytes) else key.split(":")[1]
            aid = r.get(f"conversation:{conv_name}:agent_id")
            if aid:
                return aid.decode() if isinstance(aid, (bytes, bytearray)) else aid
    return "agent_default"


@dataclass
class ConversationInfo:
    name: str
    conv_id: str
    agent_id: str
    delivery: str | None


@dataclass
class StackLine:
    idx: int
    ts: float
    kind: str
    content: str


@dataclass
class BranchInfo:
    branch_id: str
    length: int
    last_ts: str
    is_current: bool


def list_conversations(engine) -> List[ConversationInfo]:
    r = get_redis(engine)  
    infos: List[ConversationInfo] = []
    for key in r.keys("conversation:*:id"):
        conv_name = key.decode().split(":")[1] if isinstance(key, bytes) else key.split(":")[1]
        conv_id = r.get(key)
        agent_id = r.get(f"conversation:{conv_name}:agent_id")
        delivery = r.get(f"conversation:{conv_name}:delivery")
        infos.append(
            ConversationInfo(
                name=conv_name,
                conv_id=(conv_id.decode() if isinstance(conv_id, bytes) else conv_id),
                agent_id=(agent_id.decode() if isinstance(agent_id, bytes) else agent_id),
                delivery=(delivery.decode() if isinstance(delivery, bytes) else delivery),
            )
        )
    return infos


def stack_view(
    engine,
    conv_id: str,
    n: int = 10,
    branch_id: str | None = None,
    agent_id: Optional[str] = None,
) -> List[StackLine]:
    r = get_redis(engine)
    conv_id = _resolve_conv_id(r, conv_id)
    agent_id = agent_id or _resolve_agent_id(r, conv_id)
    stack = InteractionStack(r, conv_id, agent_id)
    length = stack.length(branch_id)
    if length == 0:
        return []
    lines: List[StackLine] = []
    for i in range(max(0, length - n), length):
        entry = stack.at(i, branch_id)
        state = entry.state
        if isinstance(state, UserMessageState) and state.text == "__child_finished__":
            continue
        if isinstance(state, UserMessageState):
            kind = "UserMessage"
            content = state.text
        elif isinstance(state, AssistantMessageState):
            kind = "AssistantMsg"
            content = state.content or ""
        elif isinstance(state, ToolCallState):
            kind = "ToolCall"
            content = f"{state.function_name}({state.arguments})"
        elif isinstance(state, ToolResultState):
            kind = "ToolResult"
            content = f"{state.tool_name}: {state.result}"
        else:
            kind = type(state).__name__
            content = str(state)
        lines.append(StackLine(i, entry.ts, kind, content))
    return lines


def branches(
    engine,
    conv_id: str,
    agent_id: Optional[str] = None,
) -> List[BranchInfo]:
    r = get_redis(engine)  
    conv_id = _resolve_conv_id(r, conv_id)
    agent_id = agent_id or _resolve_agent_id(r, conv_id)
    info = InteractionStack(r, conv_id, agent_id).get_branch_info()
    out: List[BranchInfo] = []
    for b in info:
        ts = b.get("last_ts")
        last_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "N/A"
        out.append(BranchInfo(b["branch_id"], b["length"], last_str, b["is_current"]))
    return out
