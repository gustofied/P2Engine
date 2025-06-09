import json

from rich.table import Table
from rich.syntax import Syntax
import typer

from .handlers.eval import best_branches, eval_diff
from ._ui import STYLES, console

app = typer.Typer()


@app.command("top")
def eval_top(
    ctx: typer.Context,
    session_id: str,
    k: int = typer.Option(20, "--k", help="Number of top branches"),
    metric: str = typer.Option("score", "--metric", help="Metric to sort by"),
) -> None:
    rows = best_branches(session_id, k=k, metric=metric)

    if not rows:
        console.print(f"[yellow]No evaluations for session {session_id}[/yellow]")
        return

    table = Table(
        title=f"Top branches for session {session_id} (metric={metric})",
        header_style=STYLES["header"],
    )
    table.add_column("Branch ID", style=STYLES["name"])
    table.add_column("Score", style=STYLES["value"])

    for bid, val in rows:
        table.add_row(bid, f"{val:.3f}")

    console.print(table)


@app.command("diff")
def eval_diff_cmd(ctx: typer.Context, ref1: str, ref2: str) -> None:
    h1, h2 = eval_diff(ref1, ref2)

    import difflib

    left = json.dumps(h1.get("meta", {}).get("eval_metrics", {}), indent=2).splitlines()
    right = json.dumps(h2.get("meta", {}).get("eval_metrics", {}), indent=2).splitlines()
    diff = difflib.unified_diff(left, right, fromfile=ref1, tofile=ref2)
    diff_text = "\n".join(diff)

    syntax = Syntax(diff_text, "diff", theme="monokai", line_numbers=True)
    console.print(syntax)
