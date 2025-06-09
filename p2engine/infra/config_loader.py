import os
from functools import lru_cache
from pathlib import Path
from typing import List

from omegaconf import OmegaConf
from pydantic import TypeAdapter

from infra.config import AppSettings, load_settings
from orchestrator.schemas.schemas import AgentConfig


def _yaml(env_var: str, default_path: str) -> dict:
    path = Path(os.getenv(env_var, default_path)).expanduser().resolve()
    if not path.exists():
        raise FileNotFoundError(f"Configuration file not found at {path}")
    return OmegaConf.to_container(OmegaConf.load(path), resolve=True)


@lru_cache
def settings() -> AppSettings:
    return load_settings()


@lru_cache
def agents() -> List[AgentConfig]:
    raw = _yaml("AGENTS_CFG", "config/agents.yml")
    data = raw.get("agents", raw if isinstance(raw, list) else [])
    return TypeAdapter(List[AgentConfig]).validate_python(data)
