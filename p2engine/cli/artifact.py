import typer

from .handlers.artifacts import cat_artifact, diff_artifacts, show_artifacts

app = typer.Typer(help="Inspect and compare stored artifacts")


@app.command("show")
def show_cmd(
    ctx: typer.Context,
    conversation_id: str,
    branch_id: str = typer.Option(None, "--branch", help="Filter by branch ID"),
    limit: int = typer.Option(50, "--limit", help="Max rows to display"),
    tag: str = typer.Option(None, "--tag", help="Filter by tag"),
    since: str = typer.Option(
        None,
        "--since",
        help="ISO timestamp, e.g. 2025-05-18T12:00:00Z (show newer only)",
    ),
) -> None:
    """List recent artifacts for a conversation."""
    engine = ctx.obj
    show_artifacts(engine, conversation_id, branch_id=branch_id, limit=limit, tag=tag, since=since)


@app.command("cat")
def cat_cmd(ctx: typer.Context, ref: str) -> None:
    """Print the payload of a single artifact."""
    engine = ctx.obj
    cat_artifact(engine, ref)


@app.command("diff")
def diff_cmd(ctx: typer.Context, ref1: str, ref2: str) -> None:
    """Unified-diff of two JSON artifacts."""
    engine = ctx.obj
    diff_artifacts(engine, ref1, ref2)
