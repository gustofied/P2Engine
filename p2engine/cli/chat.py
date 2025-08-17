import time
from rich.progress import Progress, SpinnerColumn, TextColumn
import typer

from ._ui import console
from .handlers.chat import (
    poll_response,
    resume_chat,
    send_user_message,
    start_chat,
)


def _conversation_exists(engine, conv_name: str) -> bool:
    r = engine.container.get_redis_client()
    return r.exists(f"conversation:{conv_name}:id")


app = typer.Typer()


@app.command("with")
def chat_with(ctx: typer.Context, agent_id: str) -> None:
    """Start a chat with a specific agent."""
    engine = ctx.obj

    if not engine.container.get_agent_registry().get_agent(agent_id):
        console.print(f"[red]Agent '{agent_id}' not found.[/red]")
        raise typer.Exit(code=1)

    conv_name = typer.prompt("Enter a name for this conversation").strip()
    if not conv_name:
        console.print("[red]Conversation name cannot be empty.[/red]")
        raise typer.Exit(code=1)

    if _conversation_exists(engine, conv_name):
        if typer.confirm(
            f"Conversation '{conv_name}' already exists – resume instead of starting a new one?",
            default=True,
        ):
            conversation_id, _agent = resume_chat(engine, conv_name)
            console.print(f"Resumed chat with {_agent} (Name: {conv_name}, ID: {conversation_id}). " "Type 'exit' to quit.")
            _interactive_loop(engine, conversation_id, _agent)
            return

    started = start_chat(engine, agent_id, conv_name)
    console.print(f"Entering chat with {agent_id} (Name: {conv_name}, ID: {started.conv_id}). " "Type 'exit' to quit.")
    _interactive_loop(engine, started.conv_id, agent_id)


@app.command("resume")
def chat_resume(ctx: typer.Context, conv_name: str) -> None:
    """Resume an existing conversation."""
    engine = ctx.obj

    try:
        conversation_id, agent_id = resume_chat(engine, conv_name)
    except ValueError:
        console.print(f"[red]Conversation '{conv_name}' not found.[/red]")
        raise typer.Exit(code=1)

    console.print(f"Resumed chat with {agent_id} (Name: {conv_name}, ID: {conversation_id}). " "Type 'exit' to quit.")
    _interactive_loop(engine, conversation_id, agent_id)


def _interactive_loop(engine, conversation_id: str, agent_id: str) -> None:
    """Main chat interaction loop."""
    r = engine.container.get_redis_client()

    branch_key = f"stack:{conversation_id}:{agent_id}:branch"
    current_branch = r.get(branch_key)
    if current_branch:
        current_branch = current_branch.decode() if isinstance(current_branch, bytes) else current_branch
        if current_branch != "main":
            console.print(f"[dim]Currently on branch: {current_branch}[/dim]")

    while True:
        message = typer.prompt("You")
        if message.lower() == "exit":
            break

        send_user_message(engine, conversation_id, agent_id, message)

        timeout = 60
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]Waiting for response…"),
            transient=True,
        ) as progress:
            task = progress.add_task("", total=None)
            start_time = time.time()

            while time.time() - start_time < timeout:
                reply = poll_response(engine, conversation_id, timeout=0)
                if reply:
                    console.print(f"[green]{agent_id}:[/green] {reply}")
                    break
                time.sleep(0.1)
            else:
                console.print(f"[yellow]No response from {agent_id} within {timeout} seconds.[/yellow]")

    console.print("Exiting chat mode.")
