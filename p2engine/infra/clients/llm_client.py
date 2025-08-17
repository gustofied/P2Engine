from __future__ import annotations

import os
import time
from typing import Any, Dict, List, Optional, Tuple

import litellm
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from infra.artifacts.bus import get_bus
from infra.config_loader import settings
from infra.logging.logging_config import (
    litellm_logger,
    litellm_logging_fn,
    logger,
    redirect_stdout_to_logger,
)


class LLMClient:
    def __init__(
        self,
        *,
        api_key: str,
        api_base: str,
        model: str,
        logger_fn: Optional[Any] = None,
    ) -> None:
        if not api_key:
            raise ValueError("API key is required for LLMClient")

        self.api_key = api_key
        self.api_base = api_base.rstrip("/")
        self.model = model
        self.logger_fn = logger_fn or litellm_logging_fn

        if settings().mode == "development" and os.getenv("LITELLM_LOG_LEVEL", "").lower() == "debug":
            with redirect_stdout_to_logger(litellm_logger):
                litellm._turn_on_debug()
                litellm.supports_function_calling(model=self.model)

        logger.info(
            {
                "message": "LLMClient initialized",
                "model": self.model,
                "supports_function_calling": litellm.supports_function_calling(model=self.model),
                "supports_parallel_function_calling": litellm.supports_parallel_function_calling(model=self.model),
            }
        )

    def _publish_metrics(
        self,
        *,
        conversation_id: str,
        agent_id: str | None,
        branch_id: str | None,
        episode_id: str | None,
        model: str,
        latency_ms: int,
        prompt_tokens: Optional[int],
        completion_tokens: Optional[int],
        cost_usd: Optional[float],
    ) -> None:
        try:
            bus = get_bus()
            header: Dict[str, Any] = {
                "session_id": conversation_id,
                "agent_id": agent_id or "unknown",
                "branch_id": branch_id or "main",
                "episode_id": episode_id or "",
                "role": "metrics",
                "mime": "application/json",
                "model": model,
                "latency_ms": latency_ms,
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
            }
            if cost_usd is not None:
                header["cost_usd"] = cost_usd
            bus.publish(header, {})
        except Exception as exc:
            logger.error(
                {
                    "message": "Failed to publish LLM metrics artefact",
                    "conversation_id": conversation_id,
                    "agent_id": agent_id,
                    "error": str(exc),
                },
                exc_info=True,
            )

    def _usage_from_litellm(self, resp) -> Tuple[Optional[int], Optional[int], Optional[float]]:
        usage = getattr(resp, "usage", None)
        if isinstance(usage, dict):
            prompt = usage.get("prompt_tokens")
            completion = usage.get("completion_tokens")
        else:
            prompt = getattr(usage, "prompt_tokens", None) if usage else None
            completion = getattr(usage, "completion_tokens", None) if usage else None
        hidden = getattr(resp, "_hidden_params", {}) or {}
        cost = hidden.get("response_cost")
        return prompt, completion, cost

    def query(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        conversation_id: Optional[str] = None,
        *,
        agent_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        episode_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ):
        conversation_id = conversation_id or "unknown"
        start_time = time.time()
        kwargs: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "timeout": 30,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if top_p is not None:
            kwargs["top_p"] = top_p
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice if tool_choice is not None else "auto"
        if self.logger_fn is not None:
            kwargs["logger_fn"] = self.logger_fn
        try:
            with redirect_stdout_to_logger(litellm_logger):
                response = litellm.completion(**kwargs)
            latency_ms = getattr(response, "response_ms", None)
            if latency_ms is None:
                latency_ms = int((time.time() - start_time) * 1000)
            prompt_tokens, completion_tokens, cost_usd = self._usage_from_litellm(response)
            self._publish_metrics(
                conversation_id=conversation_id,
                agent_id=agent_id,
                branch_id=branch_id,
                episode_id=episode_id,
                model=kwargs["model"],
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd,
            )
            logger.info(
                {
                    "message": "LLM query successful",
                    "conversation_id": conversation_id,
                    "model": kwargs["model"],
                    "tool_calls": (len(response.choices[0].message.tool_calls) if response.choices[0].message.tool_calls else 0),
                }
            )
            return response
        except Exception as e:
            import traceback

            logger.error(
                {
                    "message": "LLM query failed",
                    "conversation_id": conversation_id,
                    "model": kwargs.get("model", self.model),
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
                exc_info=True,
            )
            raise

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=4, max=10),
        retry=retry_if_exception_type((litellm.RateLimitError, litellm.APIConnectionError)),
    )
    async def aquery(
        self,
        messages: List[Dict[str, Any]],
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        conversation_id: Optional[str] = None,
        *,
        agent_id: Optional[str] = None,
        branch_id: Optional[str] = None,
        episode_id: Optional[str] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
    ):
        conversation_id = conversation_id or "unknown"
        start_time = time.time()
        kwargs: Dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "api_key": self.api_key,
            "api_base": self.api_base,
            "timeout": 30,
        }
        if temperature is not None:
            kwargs["temperature"] = temperature
        if top_p is not None:
            kwargs["top_p"] = top_p
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = tool_choice if tool_choice is not None else "auto"
        if self.logger_fn is not None:
            kwargs["logger_fn"] = self.logger_fn
        try:
            with redirect_stdout_to_logger(litellm_logger):
                response = await litellm.acompletion(**kwargs)
            latency_ms = getattr(response, "response_ms", None)
            if latency_ms is None:
                latency_ms = int((time.time() - start_time) * 1000)
            prompt_tokens, completion_tokens, cost_usd = self._usage_from_litellm(response)
            self._publish_metrics(
                conversation_id=conversation_id,
                agent_id=agent_id,
                branch_id=branch_id,
                episode_id=episode_id,
                model=kwargs["model"],
                latency_ms=latency_ms,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                cost_usd=cost_usd,
            )
            logger.info(
                {
                    "message": "Async LLM query successful",
                    "conversation_id": conversation_id,
                    "model": kwargs["model"],
                    "tool_calls": (len(response.choices[0].message.tool_calls) if response.choices[0].message.tool_calls else 0),
                }
            )
            return response
        except Exception as e:
            import traceback

            logger.error(
                {
                    "message": "Async LLM query failed",
                    "conversation_id": conversation_id,
                    "model": kwargs.get("model", self.model),
                    "error": str(e),
                    "traceback": traceback.format_exc(),
                },
                exc_info=True,
            )
            raise
