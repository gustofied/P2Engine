import json
from typing import Optional

import typer
from rich.table import Table
from pathlib import Path

from .handlers.config import (
    set_delivery,
    set_override,
    get_overrides,
    get_conversation_names,
    get_tool_names,
    get_persona_names,
)
from ._ui import STYLES, console

app = typer.Typer()


# ── autocompletion helpers ─────────────────────────────────────────────────────
def complete_conversation(ctx: typer.Context, incomplete: str):
    engine = ctx.obj
    names = get_conversation_names(engine)
    return [name for name in names if name.startswith(incomplete)]


def complete_tool(ctx: typer.Context, incomplete: str):
    engine = ctx.obj
    tools = get_tool_names(engine)
    return [t for t in tools if t.startswith(incomplete)]


def complete_persona(ctx: typer.Context, incomplete: str):
    personas = get_persona_names()
    return [p for p in personas if p.startswith(incomplete)]


# ── commands ───────────────────────────────────────────────────────────────────
@app.command("set-delivery")
def set_delivery_cmd(
    ctx: typer.Context,
    scope: str,
    key: str = typer.Argument(..., autocompletion=complete_conversation),
    mode: str = "ticked",
) -> None:
    engine = ctx.obj
    if mode != "ticked":
        console.print("[red]Error: Only 'ticked' delivery mode is supported.[/red]")
        raise typer.Exit(code=1)

    set_delivery(engine, scope, key, mode)
    console.print(f"[green]{scope.title()} {key} set to {mode}[/green]")


@app.command("set-behavior")
def set_behavior(
    ctx: typer.Context,
    conversation: str = typer.Argument(..., autocompletion=complete_conversation),
    template_name: str = typer.Argument(..., autocompletion=complete_persona),
    lock: bool = typer.Option(False, "--lock", help="Lock the override"),
) -> None:
    engine = ctx.obj

    conv_id = conversation
    agent_id = engine.container.get_redis_client().get(f"conversation:{conversation}:agent_id")
    if not agent_id:
        console.print(f"[red]No agent found for conversation {conversation}[/red]")
        raise typer.Exit(code=1)

    agent_id = agent_id.decode() if isinstance(agent_id, bytes) else agent_id
    patch = {"behavior_template": None if template_name.lower() == "none" else template_name}
    if lock:
        patch["lock"] = True

    set_override(engine, conv_id, agent_id, patch)
    console.print(f"[green]Behavior for {conversation} set to {template_name} (lock={lock})[/green]")


@app.command("set-tools")
def set_tools(
    ctx: typer.Context,
    conversation: str = typer.Argument(..., autocompletion=complete_conversation),
    tools: str = typer.Argument(..., help="Comma-separated tool names or 'none'"),
) -> None:
    engine = ctx.obj

    tool_list = [] if tools.lower() == "none" else [t.strip() for t in tools.split(",") if t.strip()]
    valid_tools = set(get_tool_names(engine))
    unknown = [t for t in tool_list if t not in valid_tools]
    if unknown:
        console.print(f"[red]Unknown tools: {', '.join(unknown)}[/red]")
        raise typer.Exit(code=1)

    conv_id = conversation
    agent_id = engine.container.get_redis_client().get(f"conversation:{conversation}:agent_id")
    if not agent_id:
        console.print(f"[red]No agent found for conversation {conversation}[/red]")
        raise typer.Exit(code=1)

    agent_id = agent_id.decode() if isinstance(agent_id, bytes) else agent_id
    set_override(engine, conv_id, agent_id, {"tools": tool_list})
    console.print(f"[green]Tool overrides set for conversation {conversation}: " f"{tool_list or 'none'}[/green]")


@app.command("show-overrides")
def show_overrides_cmd(
    ctx: typer.Context,
    conversation: str = typer.Argument(..., autocompletion=complete_conversation),
) -> None:
    engine = ctx.obj

    conv_id = conversation
    agent_id = engine.container.get_redis_client().get(f"conversation:{conversation}:agent_id")
    if not agent_id:
        console.print(f"[red]No agent found for conversation {conversation}[/red]")
        raise typer.Exit(code=1)

    agent_id = agent_id.decode() if isinstance(agent_id, bytes) else agent_id
    data = get_overrides(engine, conv_id, agent_id)

    if data:
        table = Table(
            title=f"Overrides for {conversation} (ID: {conv_id})",
            header_style=STYLES["header"],
        )
        table.add_column("Key", style=STYLES["name"])
        table.add_column("Value", style=STYLES["value"])
        for k, v in data.items():
            table.add_row(k, json.dumps(v))
        console.print(table)
    else:
        console.print(f"[yellow]No overrides set for {conversation}[/yellow]")


@app.command("show-tools")
def show_tools_cmd(ctx: typer.Context) -> None:
    engine = ctx.obj
    tools = engine.container.get_tool_registry().get_tools()

    if not tools:
        console.print("[yellow]No tools are registered.[/yellow]")
        return

    table = Table(title="Available Tools", header_style=STYLES["header"])
    table.add_column("Tool Name", style=STYLES["name"])
    table.add_column("Description", style=STYLES["value"])

    for t in tools:
        table.add_row(t.name, t.description or "")

    console.print(table)
