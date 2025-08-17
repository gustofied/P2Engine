from __future__ import annotations

import shlex
import sys
import traceback
from typing import List

import click
import typer
from rich.console import Console
from rich.table import Table

from cli.__main__ import app as root_app

console = Console()


def _collect_commands(root: typer.Typer) -> List[str]:
    def _walk(group: typer.Typer, prefix: str = "") -> List[str]:
        out: List[str] = []
        for cmd_info in getattr(group, "registered_commands", []):
            out.append(f"{prefix}{cmd_info.name}")
        for grp_info in getattr(group, "registered_groups", []):
            out.extend(_walk(grp_info.typer_instance, prefix=f"{prefix}{grp_info.name} "))
        return out

    return _walk(root)


def _fuzzy(name: str, candidates: List[str]) -> str | None:
    import difflib

    hits = difflib.get_close_matches(name, candidates, n=1, cutoff=0.6)
    return hits[0] if hits else None


class _REPL:
    PROMPT = "p2engine▸ "

    def __init__(self, ctx: typer.Context) -> None:
        self.ctx = ctx
        self.history: List[str] = []

    # ------------------------------------------------- helpers

    def _print_help(self) -> None:
        cmds = _collect_commands(root_app)
        table = Table(title="Available p2engine commands", show_lines=False)
        table.add_column("Syntax", style="cyan")
        for c in sorted(cmds):
            table.add_row(c)
        console.print(table)
        console.print("[dim]All root-level Typer options (e.g. --help) also work.[/dim]")

    def _run_command(self, raw: str) -> None:
        if not raw.strip():
            return

        if raw.strip() in {"help", "?", "--help"}:
            self._print_help()
            return
        if raw.strip() in {"exit", "quit"}:
            raise typer.Exit()
        if raw.strip() == "history":
            for idx, cmd in enumerate(self.history, 1):
                console.print(f"[green]{idx:>2}[/green]  {cmd}")
            return
        if raw.strip() == "!!":
            if not self.history:
                console.print("[yellow]No history yet.[/yellow]")
                return
            raw = self.history[-1]
            console.print(f"[dim]→ {raw}[/dim]")
        elif raw.strip().startswith("!"):
            try:
                n = int(raw.strip()[1:])
                raw = self.history[n - 1]
                console.print(f"[dim]→ {raw}[/dim]")
            except (ValueError, IndexError):
                console.print("[red]Invalid history reference[/red]")
                return

        self.history.append(raw)
        try:
            argv = shlex.split(raw)
        except ValueError as exc:
            console.print(f"[red]Parse error:[/red] {exc}")
            return

        try:
            root_app(argv, obj=self.ctx.obj, standalone_mode=False)

        except click.UsageError as ue:
            target = getattr(ue, "cmd_name", getattr(ue, "option_name", ""))
            suggestion = _fuzzy(target, _collect_commands(root_app))
            if suggestion:
                console.print(f"[yellow]No such command/option:[/yellow] {target}. " f"Did you mean [green]{suggestion}[/green]?")
            else:
                console.print(ue.format_message())

        except click.ClickException as ce:
            console.print(ce.format_message())

        except typer.Exit as e:
            if e.exit_code != 0:
                console.print(f"[red]Command exited with code {e.exit_code}[/red]")
        except SystemExit as e:
            if e.code not in (0, None):
                console.print(f"[red]Command aborted (code {e.code})[/red]")
        except Exception:
            console.print("[bold red]Unhandled exception while executing command:[/bold red]")
            console.print(traceback.format_exc())


    def run(self) -> None:
        console.print("[bold magenta]p2engine interactive shell[/bold magenta] " "(type 'help' or '?' for commands, 'quit' to exit)\n")
        while True:
            try:
                line = console.input(self.PROMPT)
            except (KeyboardInterrupt, EOFError):
                console.print()
                break
            self._run_command(line)


shell_app = typer.Typer(
    name="shell",
    help="Launch an interactive p2engine REPL.",
    invoke_without_command=True,
    no_args_is_help=False,
)


@shell_app.callback(invoke_without_command=True)
def _entry(ctx: typer.Context) -> None:
    _REPL(ctx).run()


shell = shell_app
