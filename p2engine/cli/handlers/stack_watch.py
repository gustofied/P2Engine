from __future__ import annotations

import time
from typing import Optional

from rich.live import Live
from rich.table import Table

from cli.handlers.conversation import (
    _resolve_agent_id,
    _resolve_conv_id,
    stack_view,
)
from cli.utils.compat import get_redis



def _snapshot(
    engine,
    conv_id: str,
    *,
    agent_id: str,
    branch_id: Optional[str],
    limit: int,
) -> Table:
    """Render the latest slice of the interaction stack as a Rich Table."""
    rows = stack_view(
        engine,
        conv_id,
        n=limit,
        branch_id=branch_id,
        agent_id=agent_id,
    )

    table = Table(show_lines=False)
    table.add_column("idx", justify="right")
    table.add_column("kind")
    table.add_column("content", overflow="fold")

    for ln in rows:
        snippet = (ln.content[:97] + "…") if len(ln.content) > 100 else ln.content
        table.add_row(str(ln.idx), ln.kind, snippet)

    return table


def watch_stack(
    engine,
    conv_name_or_id: str,
    branch_id: str | None = None,
    agent_id: str | None = None,
    interval: float = 1.5,
    limit: int = 25,
) -> None:
    """
    Live-refresh an interaction stack in the terminal.

    * interval – refresh cadence in seconds
    * limit    – max number of stack entries to show
    """
    r = get_redis(engine)

    conv_id = _resolve_conv_id(r, conv_name_or_id)
    agent_id = agent_id or _resolve_agent_id(r, conv_name_or_id)

    refresh_fps = max(1, int(1 / interval))

    with Live(
        _snapshot(engine, conv_id, agent_id=agent_id, branch_id=branch_id, limit=limit),
        refresh_per_second=refresh_fps,
    ) as live:
        while True:
            time.sleep(interval)
            live.update(_snapshot(engine, conv_id, agent_id=agent_id, branch_id=branch_id, limit=limit))
