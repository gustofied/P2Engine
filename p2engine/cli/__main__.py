from __future__ import annotations

import typer

from .agents import app as agents_app
from .artifact import app as artifact_app
from .chat import app as chat_app
from .config import app as config_app
from .conversation import app as conversation_app
from .eval import app as eval_app
from runtime.engine import Engine
from runtime.rollout.cli import app as rollout_app 
from .ledger import app as ledger_app


app = typer.Typer(help="p2engine command-line interface")

_engine: Engine | None = None


@app.callback()
def main(ctx: typer.Context) -> None:
    """Initialise a singleton Engine and expose it via `ctx.obj`."""
    global _engine

    if _engine is None:
        _engine = Engine()
        _engine.start(block=False)

    ctx.obj = _engine

app.add_typer(agents_app, name="agent", help="Manage agents")
app.add_typer(chat_app, name="chat", help="Chat with agents")
app.add_typer(config_app, name="config", help="Runtime configuration")
app.add_typer(conversation_app, name="conversation", help="Conversation inspection")
app.add_typer(eval_app, name="eval", help="Evaluation helpers")
app.add_typer(artifact_app, name="artifact", help="Artifact inspection / diff")
app.add_typer(rollout_app, name="rollout", help="Run roll-outs")
app.add_typer(ledger_app, name="ledger", help="Canton ledger operations")


from .shell import shell as shell_app  

app.add_typer(shell_app, name="shell", help="Interactive multi-command shell")
