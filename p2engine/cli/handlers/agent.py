from __future__ import annotations

from dataclasses import dataclass

from cli.utils.compat import get_agent_registry  # ← unified helper


@dataclass
class AgentsListed:
    names: list[str]


def list_agents(engine) -> AgentsListed:
    reg = get_agent_registry(engine)  # <-- shim
    return AgentsListed(list(reg.list_agents().keys()))
