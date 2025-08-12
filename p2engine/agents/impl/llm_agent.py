# TODO, Add IAgent type hints in the implementations?
import json
from typing import Dict, List, Optional, Union

import redis

from agents.persona_registry import get_required_tools
from infra.clients.llm_client import LLMClient
from infra.clients.redis_client import get_redis
from infra.logging.logging_config import logger
from infra.utils.session_helpers import current_episode_id
from orchestrator.registries import ToolRegistry
from orchestrator.renderer.template_manager import TemplateManager
from orchestrator.schemas.schemas import AgentConfig, AskSchema, FunctionCallSchema, ReplySchema


class LLMAgent:
    def __init__(
        self,
        *,
        agent_id: str,
        model: str,
        tool_names: List[str],
        behavior_template: str | None,
        llm_client: LLMClient,
        tool_registry: ToolRegistry,
        template_manager: TemplateManager,
        redis_client: Optional[redis.Redis] = None,
        config: AgentConfig | None = None,
    ) -> None:
        self.agent_id = agent_id
        self.default_model = model
        self._default_tool_names = list(tool_names)
        self.behavior_template = behavior_template
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.template_manager = template_manager
        self.redis: redis.Redis = redis_client or get_redis()
        self.config = config

    async def run(
        self,
        input: AskSchema,
        *,
        overrides: Optional[Dict] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        tools_override: Optional[List[str]] = None,
    ) -> Union[ReplySchema, FunctionCallSchema]:
        """
        Entry point invoked by the runtime.  Builds the full prompt, resolves the
        active branch / episode and finally executes an *async* LLM call.
        """
        # ----- resolve overrides ----------------------------------------
        if overrides is None:
            redis_key = f"agent:{self.agent_id}:{input.conversation_id}:override"
            try:
                overrides = json.loads(self.redis.get(redis_key) or "{}")
            except json.JSONDecodeError:
                logger.error("Invalid JSON in override for %s / %s", self.agent_id, input.conversation_id)
                overrides = {}

        behavior_template = overrides.get("behavior_template", self.behavior_template)
        tool_names: List[str] = tools_override if tools_override is not None else overrides.get("tools", self._default_tool_names)
        tool_names = list(tool_names)

        # ensure required tools are included
        if behavior_template:
            required = get_required_tools(behavior_template)
            missing = required - set(tool_names)
            if missing:
                logger.warning(
                    "Persona '%s' requested but tools %s were missing – auto-adding.",
                    behavior_template,
                    sorted(missing),
                )
                tool_names.extend(sorted(missing))

        # ----- build OpenAI function-tool schemas -----------------------
        tool_schemas = [self.tool_registry.get_tool_by_name(n).schema for n in tool_names if self.tool_registry.get_tool_by_name(n)]

        # ----- build messages ------------------------------------------
        messages: List[dict] = [self._get_system_message(tool_schemas)]
        if behavior_template:
            messages.append(self._get_persona_message(behavior_template, input))
        messages += input.history

        # ----- episode / branch lookup ---------------------------------
        branch_id_raw = self.redis.get(f"stack:{input.conversation_id}:{self.agent_id}:branch")
        branch_id = (
            branch_id_raw if isinstance(branch_id_raw, str) else branch_id_raw.decode(errors="replace") if branch_id_raw else "main"
        )
        episode_id = current_episode_id(self.redis, input.conversation_id, self.agent_id, branch_id)

        # ----- parameter bag for LiteLLM -------------------------------
        base_params: Dict[str, object] = {
            "messages": messages,
            "model": overrides.get("model", model or self.default_model),
            "temperature": overrides.get("temperature", 0.7 if temperature is None else temperature),
            "top_p": overrides.get("top_p", 1.0 if top_p is None else top_p),
        }
        if tool_schemas:
            base_params["tools"] = [{"type": "function", "function": s} for s in tool_schemas]
            base_params["tool_choice"] = "auto"

        # ----- fire LLM -------------------------------------------------
        response = await self.llm_client.aquery(
            conversation_id=input.conversation_id,
            agent_id=self.agent_id,
            branch_id=branch_id,
            episode_id=episode_id,
            **base_params,
        )

        # ----- materialise ---------------------------------------------
        message = response.choices[0].message
        if message.content:
            return ReplySchema(message=message.content)

        if message.tool_calls:
            tc = message.tool_calls[0]
            return FunctionCallSchema(
                function_name=tc.function.name,
                arguments=json.loads(tc.function.arguments),
            )

        return ReplySchema(message="No response generated.")


    def _get_system_message(self, tool_schemas: List[dict]) -> dict:
        template = self.template_manager.get_template("system_message.j2")
        return {"role": "system", "content": template.render(tools=tool_schemas)}

    def _get_persona_message(self, behavior_template: str, input: AskSchema) -> dict:
        template = self.template_manager.get_template(f"personas/{behavior_template}.j2")
        last_user_msg = next((m["content"] for m in reversed(input.history) if m["role"] == "user"), "")
        return {"role": "system", "content": template.render(question=last_user_msg)}
