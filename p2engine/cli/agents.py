import typer
from rich.table import Table

from .handlers.agent import list_agents
from ._ui import STYLES, console

app = typer.Typer()


@app.command("list")
def list_agents_command(ctx: typer.Context) -> None:
    engine = ctx.obj
    res = list_agents(engine)

    table = Table(title="Registered Agents", header_style=STYLES["header"])
    table.add_column("Agent Name", style=STYLES["name"])

    for name in res.names:
        table.add_row(name)

    console.print(table)
