from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import time

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

from ._ui import STYLES, console

from orchestrator.interactions.branch import checkout as _checkout
from orchestrator.interactions.branch import rewind as _rewind
from orchestrator.interactions.branch import fork as _fork

app = typer.Typer()


def _resolve_conv_id(r, conv_name_or_id: str) -> str:
    cid = r.get(f"conversation:{conv_name_or_id}:id")
    if cid:
        return cid.decode() if isinstance(cid, (bytes, bytearray)) else cid
    return conv_name_or_id


def _resolve_agent_id(r, conv_name_or_id: str) -> str:
    aid = r.get(f"conversation:{conv_name_or_id}:agent_id")
    if aid:
        return aid.decode() if isinstance(aid, (bytes, bytearray)) else aid

    # Try to find agent_id by conv_id
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

        # Skip synthetic markers
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


@app.command("list")
def list_conversations_cmd(ctx: typer.Context) -> None:
    """List all active conversations."""
    engine = ctx.obj
    infos = list_conversations(engine)

    if not infos:
        console.print("[yellow]No active conversations.[/yellow]")
        return

    table = Table(title="Active Conversations", header_style=STYLES["header"])
    table.add_column("Name", style=STYLES["name"])
    table.add_column("Agent", style=STYLES["name"])
    table.add_column("ID", style=STYLES["value"])
    table.add_column("Delivery Mode", style=STYLES["kind"])

    for info in infos:
        mode = info.delivery or "N/A"
        table.add_row(info.name, info.agent_id, info.conv_id, mode)

    console.print(table)


@app.command("stack")
def stack_cmd(
    ctx: typer.Context,
    conversation: str,
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Specify agent ID"),
    n: int = typer.Option(10, "--n", help="Number of recent interactions"),
    branch_id: Optional[str] = typer.Option(None, "--branch", help="Specify branch ID"),
) -> None:
    """Show the conversation stack."""
    engine = ctx.obj
    lines = stack_view(engine, conversation, n=n, branch_id=branch_id, agent_id=agent_id)

    if not lines:
        console.print(f"[yellow]No interactions for conversation={conversation}, " f"branch={branch_id or 'current'}.[/yellow]")
        return

    table = Table(title=f"Stack for conversation {conversation}", header_style=STYLES["header"])
    table.add_column("Index", style=STYLES["value"])
    table.add_column("Timestamp", style=STYLES["timestamp"])
    table.add_column("Kind", style=STYLES["kind"])
    table.add_column("Content", style=STYLES["content"])

    for ln in lines:
        ts = datetime.fromtimestamp(ln.ts).strftime("%H:%M:%S")
        table.add_row(str(ln.idx), ts, ln.kind, ln.content)

    console.print(table)


@app.command("branches")
def branches_cmd(
    ctx: typer.Context,
    conversation: str,
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Specify agent ID"),
) -> None:
    """Show all branches for a conversation."""
    engine = ctx.obj
    rows = branches(engine, conversation, agent_id=agent_id)

    table = Table(title=f"Branches for conversation {conversation}", header_style=STYLES["header"])
    table.add_column("Branch ID", style=STYLES["name"])
    table.add_column("Length", style=STYLES["value"])
    table.add_column("Last Timestamp", style=STYLES["timestamp"])
    table.add_column("Current", style=STYLES["value"])

    for r in rows:
        mark = "*" if r.is_current else ""
        table.add_row(r.branch_id, str(r.length), r.last_ts, mark)

    console.print(table)


@app.command("rewind")
def rewind_cmd(
    ctx: typer.Context,
    conversation: str,
    idx: int = typer.Argument(..., help="Index to rewind to (0-based)"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Specify agent ID"),
    create_branch: bool = typer.Option(True, "--branch/--no-branch", help="Create new branch from rewind point"),
    branch_name: Optional[str] = typer.Option(None, "--name", help="Name for the new branch (auto-generated if not provided)"),
) -> None:
    """Rewind the conversation to a specific index."""
    engine = ctx.obj
    r = engine.container.get_redis_client()
    conv_id = _resolve_conv_id(r, conversation)
    aid = agent_id or _resolve_agent_id(r, conversation)

    stack = InteractionStack(r, conv_id, aid)
    original_branch = stack.current_branch()
    original_length = stack.length()

    if create_branch:
        # Fork from the rewind point to create new branch
        new_branch_id = _fork(stack, idx)

        # Use custom name if provided
        if branch_name:
            # Note: In a real implementation, you might want to validate the branch name
            # and handle collisions. For now, we'll just use the generated ID.
            console.print(f"[green]Created new branch '{new_branch_id}' from index {idx}[/green]")
        else:
            console.print(f"[green]Created new branch {new_branch_id} from index {idx}[/green]")

        console.print(f"[dim]Original branch '{original_branch}' preserved with {original_length} messages[/dim]")
        console.print(f"[green]Now on branch {new_branch_id} at index {idx}[/green]")

        # Clean up state for the new branch
        branch_id = new_branch_id
        episode_key = f"stack:{conv_id}:{aid}:episode:{branch_id}"
        rounds_key = f"round_by_branch:{conv_id}:{aid}:{branch_id}"

        # Delete episode and round tracking for new branch
        r.delete(episode_key)
        r.delete(rounds_key)

    else:
        # Direct rewind without creating a branch (destructive)
        try:
            _rewind(stack, idx)

            # Clean up associated Redis keys for proper state reset
            branch_id = stack.current_branch()
            episode_key = f"stack:{conv_id}:{aid}:episode:{branch_id}"
            rounds_key = f"round_by_branch:{conv_id}:{aid}:{branch_id}"

            # Delete episode and round tracking
            r.delete(episode_key)
            r.delete(rounds_key)

            # Clean up any tool call references beyond the rewind point
            toolcall_ref_key = f"stack:{conv_id}:{aid}:toolcall_ref"
            for ref_key in r.hkeys(toolcall_ref_key):
                r.hdel(toolcall_ref_key, ref_key)

            console.print(f"[yellow]⚠️  Rewound branch '{branch_id}' to index {idx} (destructive)[/yellow]")
            console.print(f"[dim]Messages after index {idx} have been permanently removed[/dim]")

        except Exception as exc:
            console.print(f"[red]{exc}[/red]")


@app.command("checkout")
def checkout_cmd(
    ctx: typer.Context,
    conversation: str,
    branch_id: str = typer.Argument(..., help="Branch ID to switch to"),
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Specify agent ID"),
) -> None:
    """Switch to a different branch."""
    engine = ctx.obj
    r = engine.container.get_redis_client()
    conv_id = _resolve_conv_id(r, conversation)
    aid = agent_id or _resolve_agent_id(r, conversation)

    stack = InteractionStack(r, conv_id, aid)

    try:
        _checkout(stack, branch_id)
        console.print(f"[green]Checked out branch {branch_id}.[/green]")
    except Exception as exc:
        console.print(f"[red]{exc}[/red]")


@app.command("prune")
def prune_branches_cmd(
    ctx: typer.Context,
    conversation: str,
    agent_id: Optional[str] = typer.Option(None, "--agent-id", help="Specify agent ID"),
    keep_days: int = typer.Option(7, "--keep-days", help="Keep branches modified within N days"),
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Show what would be deleted without deleting"),
) -> None:
    """Prune old branches from a conversation."""
    engine = ctx.obj
    r = engine.container.get_redis_client()
    conv_id = _resolve_conv_id(r, conversation)
    aid = agent_id or _resolve_agent_id(r, conversation)

    stack = InteractionStack(r, conv_id, aid)
    branches = stack.get_branch_info()
    current_branch = stack.current_branch()

    cutoff_ts = time.time() - (keep_days * 86400)
    to_delete = []

    for branch_info in branches:
        bid = branch_info["branch_id"]
        last_ts = branch_info.get("last_ts", 0)

        # Never delete main or current branch
        if bid == "main" or bid == current_branch:
            continue

        if last_ts < cutoff_ts:
            to_delete.append((bid, last_ts))

    if not to_delete:
        console.print("[yellow]No branches to prune[/yellow]")
        return

    table = Table(title=f"Branches to {'Delete' if not dry_run else 'Prune'}")
    table.add_column("Branch ID", style="red")
    table.add_column("Last Modified", style="dim")

    for bid, ts in to_delete:
        last_modified = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "Unknown"
        table.add_row(bid, last_modified)

    console.print(table)

    if not dry_run:
        for bid, _ in to_delete:
            branch_key = f"stack:{conv_id}:{aid}:{bid}"
            r.delete(branch_key)
            console.print(f"[green]Deleted branch {bid}[/green]")
    else:
        console.print("\n[dim]Run with --execute to actually delete these branches[/dim]")
