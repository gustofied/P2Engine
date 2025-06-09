from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class ActionConfig(BaseModel):
    type: str
    event_type: str
    fields: dict
    sender_id: str
    model_config = ConfigDict(extra="forbid")


class TaskConfig(BaseModel):
    id: str
    action: ActionConfig
    parameters: Optional[dict] = None
    model_config = ConfigDict(extra="forbid")


class DependencyConfig(BaseModel):
    task_id: str
    depends_on: str
    model_config = ConfigDict(extra="forbid")


class ProcessConfig(BaseModel):
    name: str
    tasks: List[TaskConfig]
    dependencies: List[DependencyConfig] = []
    model_config = ConfigDict(extra="forbid")


class SystemConfig(BaseModel):
    id: str
    type: str
    process: str
    agent_ids: List[str]
    model_config = ConfigDict(extra="forbid")


class SubscriptionConfig(BaseModel):
    pattern: str
    task: str
    queue: str | None = None
    model_config = ConfigDict(extra="forbid")
