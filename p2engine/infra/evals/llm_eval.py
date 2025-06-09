from __future__ import annotations

import json
from json import JSONDecodeError
from typing import Any, Dict, Optional, Tuple

from jsonschema import validate, ValidationError

from infra.async_utils import run_async
from infra.clients.llm_client import LLMClient


class LLMEvaluator:
    """
    Generic helper for “LLM-backed” evaluators.

    * `build_messages(payload)` should return the prompt as a list
      of OpenAI-style chat messages.
    * `parse_result(raw)` must return either:

        1. ``(score, metrics)`` **or**
        2. ``(score, metrics, comment)``

      where:
        * *score* is a float in **[0.0 – 1.0]**
        * *metrics* is a *dict[str, float]*
        * *comment* (optional) is a free-form review string
    """

    model: str = "openai/gpt-4o-mini"
    response_schema: Dict[str, Any] | None = None
    _MAX_ATTEMPTS = 3

    def __init__(self, llm_client: LLMClient) -> None:
        self._llm = llm_client

    # --------------------------------------------------------------------- #
    # Public entry-point
    # --------------------------------------------------------------------- #
    def __call__(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        score, metrics, comment = run_async(self.score_async(payload))
        out: Dict[str, Any] = {
            "score": score,
            "metrics": metrics,
        }
        if comment is not None:
            out["comment"] = comment
        return out

    # --------------------------------------------------------------------- #
    # Core async logic
    # --------------------------------------------------------------------- #
    async def score_async(self, payload: Dict[str, Any]) -> Tuple[float, Dict[str, float], Optional[str]]:
        """
        Returns ``(score, metrics, comment)``.
        ``comment`` may be *None* if the evaluator produced none.
        """
        msgs = self.build_messages(payload)

        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            resp = await self._llm.aquery(
                conversation_id="eval",
                messages=msgs,
                model=self.model,
                temperature=0.5,
            )
            raw = (resp.choices[0].message.content or "").strip()

            try:
                # ------------------------------------------------------------------
                # Optional JSON schema validation
                # ------------------------------------------------------------------
                if self.response_schema is not None:
                    obj = json.loads(raw)
                    validate(instance=obj, schema=self.response_schema)

                parsed = self.parse_result(raw)

                # Flexibly support 2-tuple or 3-tuple returns ----------------------
                if isinstance(parsed, tuple):
                    if len(parsed) == 3:
                        score, metrics, comment = parsed
                    elif len(parsed) == 2:
                        score, metrics = parsed
                        comment = None
                    else:
                        raise ValueError("parse_result() must return 2 or 3 values " f"(got {len(parsed)})")
                else:
                    raise ValueError("parse_result() did not return a tuple")

                return float(score), metrics, comment
            except (JSONDecodeError, ValidationError, ValueError) as err:
                if attempt == self._MAX_ATTEMPTS:
                    raise RuntimeError(f"Judge returned invalid JSON after {attempt} attempts: {err}") from err

                # Tell the model to try again -------------------------------------
                msgs.append(
                    {
                        "role": "system",
                        "content": (
                            "❌ Your previous response was not valid JSON. " "Reply again with **ONLY** the required JSON object."
                        ),
                    }
                )

        # Should never reach here
        raise RuntimeError("Unexpected judge failure")

    # --------------------------------------------------------------------- #
    # Interfaces for subclasses
    # --------------------------------------------------------------------- #
    def build_messages(self, payload: Dict[str, Any]) -> list[dict]:
        raise NotImplementedError

    def parse_result(self, raw: str) -> Tuple[float, Dict[str, float], Optional[str]]:  # noqa: D401
        """
        Default “bare-bones” parser: treat the raw string as a bare score.
        """
        try:
            return float(raw), {}, None
        except ValueError:
            return 0.0, {}, None
