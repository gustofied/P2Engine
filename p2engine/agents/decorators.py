# TODO This file and everything inside should be in the tools module
import hashlib
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Type

import redis
from pydantic import BaseModel, ValidationError

from agents.interfaces import ITool
from orchestrator.registries import tool_registry
from orchestrator.schemas.schemas import ToolConfig
from tools.constants import HELPER_KWARGS

logger = logging.getLogger(__name__)


class FunctionTool(ITool):
    def __init__(self, func: Callable[..., Any], config: ToolConfig):
        self.func = func
        self.config = config

        self.name = config.name
        self.description = config.description
        self.input_schema = config.input_schema
        self.output_schema = config.output_schema
        self.cache_ttl = config.cache_ttl

    def execute(self, *, redis_client: Optional[redis.Redis] = None, **kwargs: Any) -> Dict[str, Any]:
        helper_keys = set(HELPER_KWARGS) | {"branch_id"}

        context_params = {k: kwargs.get(k) for k in helper_keys if k in kwargs}

        if self.config.requires_context:
            input_params = kwargs  
        else:
            input_params = {k: v for k, v in kwargs.items() if k not in helper_keys}
        if self.cache_ttl is not None and redis_client is not None:
            cache_key = f"tool_cache:{self.name}:" f"{hashlib.sha1(json.dumps(input_params, sort_keys=True).encode()).hexdigest()}"
            if cached := redis_client.get(cache_key):
                result = json.loads(cached)
                result["cache_status"] = "hit"
                return result
        try:
            if self.input_schema is not None:
                validated_input = self.input_schema(**input_params)
                func_kwargs = validated_input.dict()
            else:
                func_kwargs = input_params
            if self.config.requires_context:
                func_kwargs.update(context_params)

            result = self.func(**func_kwargs)

            if isinstance(result, dict):
                output = result.copy()
                output.setdefault("status", "success")
                output.setdefault("data", None)
                output.setdefault("message", "")
            else:
                output = {"status": "success", "data": result, "message": ""}

            if self.output_schema is not None:
                try:
                    output = self.output_schema(**output).dict()
                except ValidationError as err:
                    logger.error("Output validation failed for '%s': %s", self.name, err)
                    return {"status": "error", "message": "Output validation failed"}

            if self.cache_ttl is not None and redis_client is not None:
                cache_payload = output.copy()
                cache_payload.pop("cache_status", None)
                redis_client.set(cache_key, json.dumps(cache_payload), ex=self.cache_ttl)

            output["cache_status"] = "miss"

        except Exception as exc:
            logger.error("Error executing tool '%s': %s", self.name, exc, exc_info=True)
            output = {"status": "error", "message": str(exc), "error_type": type(exc).__name__}
        try:
            from infra.artifacts.bus import get_bus
            from infra.artifacts.schema import ArtifactHeader, current_timestamp, generate_ref

            hdr: ArtifactHeader = {
                "ref": generate_ref(),
                "session_id": context_params.get("conversation_id", "NA"),
                "agent_id": context_params.get("creator_id", "system"),
                "branch_id": context_params.get("branch_id", "main"),
                "state_id": "",
                "type": "tool_result",
                "mime": "application/json",
                "ts": current_timestamp(),
                "meta": {},
            }
            get_bus().publish(hdr, output)
        except Exception as _exc:
            logger.debug("ArtifactBus publish failed (non-fatal): %s", _exc)

        return output

    @property
    def schema(self) -> Dict[str, Any]:
        if self.input_schema is not None:
            schema = self.input_schema.schema()
            parameters = {
                "type": "object",
                "properties": schema.get("properties", {}),
                "required": schema.get("required", []),
            }
        else:
            parameters = {"type": "object", "properties": {}, "required": []}

        return {
            "name": self.name,
            "description": self.description,
            "parameters": parameters,
        }

    @property
    def post_effects(self) -> Optional[List[str]]:
        return self.config.post_effects


def function_tool(
    *,
    name: str,
    description: str | None = None,
    input_schema: Optional[Type[BaseModel]] = None,
    output_schema: Optional[Type[BaseModel]] = None,
    post_effects: Optional[List[str]] = None,
    requires_context: bool = False,
    cache_ttl: Optional[int] = None,
    side_effect_free: bool = False,
    dedup_ttl: Optional[int] = None,
    reflect: bool = False,
):
    def decorator(func: Callable[..., Any]):
        cfg = ToolConfig(
            name=name,
            description=description or (func.__doc__ or "").strip() or "",
            input_schema=input_schema,
            output_schema=output_schema,
            post_effects=post_effects,
            requires_context=requires_context,
            cache_ttl=cache_ttl,
            side_effect_free=side_effect_free,
            dedup_ttl=dedup_ttl,
            reflect=reflect,
        )
        tool_instance = FunctionTool(func, cfg)
        if tool_registry.register(tool_instance):
            logger.info("Registered tool: %s", cfg.name)
        return func

    return decorator
