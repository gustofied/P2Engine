from typing import Dict, List, Literal, Optional, Type, Union

from pydantic import BaseModel, ConfigDict, Field


class AskSchema(BaseModel):
    history: List[dict]
    conversation_id: str
    model_config = ConfigDict(extra="forbid")


class ReplySchema(BaseModel):
    message: str
    model_config = ConfigDict(extra="forbid")


class FunctionCallSchema(BaseModel):
    function_name: str
    arguments: dict
    model_config = ConfigDict(extra="forbid")


class LLMAgentConfig(BaseModel):
    type: Literal["llm"]
    id: str
    llm_model: str = Field(default="openai/gpt-4.1")
    behavior_template: Optional[str] = None
    tools: List[str] = Field(default_factory=list)
    render_policy: Optional[str] = None
    enable_self_reflection: bool = False
    reflection_agent_id: Optional[str] = None
    model_config = ConfigDict(extra="forbid")


class RuleBasedAgentConfig(BaseModel):
    type: Literal["rule_based"]
    id: str
    rules: Dict[str, str]
    model_config = ConfigDict(extra="forbid")


class HumanInLoopAgentConfig(BaseModel):
    type: Literal["human_in_loop"]
    id: str
    callback_url: Optional[str]
    model_config = ConfigDict(extra="forbid")


AgentConfig = Union[LLMAgentConfig, RuleBasedAgentConfig, HumanInLoopAgentConfig]


class ToolConfig(BaseModel):
    name: str
    description: str = ""
    input_schema: Optional[Type[BaseModel]] = None
    output_schema: Optional[Type[BaseModel]] = None
    post_effects: Optional[List[str]] = None
    requires_context: bool = False
    cache_ttl: Optional[int] = None
    side_effect_free: bool = False
    dedup_ttl: Optional[int] = None
    reflect: bool = False
