from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import yaml
from pydantic import BaseModel, Field, ValidationError


class EvalSpec(BaseModel):
    evaluator_id: str
    metric: str = "score"
    prompts: List[str] = Field(default_factory=list)
    rubric: Optional[str] = None
    judge_version: Optional[str] = None
    timeout_sec: int = 900


class TeamSpec(BaseModel):
    initial_message: Optional[str] = None
    base: Dict[str, Any] = Field(default_factory=dict)
    variants: Union[List[Dict[str, Any]], Dict[str, List[Any]]] = Field(default_factory=list)
    eval: Optional[EvalSpec] = None


class MultiRolloutSpec(BaseModel):
    teams: Dict[str, TeamSpec]

    @classmethod
    def load(cls, path: Union[str, Path]) -> "MultiRolloutSpec":
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        try:
            return cls(**data)
        except ValidationError as exc:
            if not isinstance(data.get("teams"), dict):
                raise ValueError("Top-level YAML key must be `teams:` mapping team-id → config.") from exc
            raise


class RolloutSpec(MultiRolloutSpec):
    @classmethod
    def load(cls, path):
        raw = Path(path).read_text(encoding="utf-8")
        data = yaml.safe_load(raw) or {}
        if "teams" in data:
            return MultiRolloutSpec.model_validate(data)
        team_id = data.get("team_id") or "legacy_team"
        wrapped = {"teams": {team_id: {k: v for k, v in data.items() if k != "team_id"}}}
        return MultiRolloutSpec.model_validate(wrapped)
