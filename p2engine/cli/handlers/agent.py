from __future__ import annotations

from dataclasses import dataclass

from cli.utils.compat import get_agent_registry 


@dataclass
class AgentsListed:
    names: list[str]


def list_agents(engine) -> AgentsListed:
    reg = get_agent_registry(engine) 
    return AgentsListed(list(reg.list_agents().keys()))
