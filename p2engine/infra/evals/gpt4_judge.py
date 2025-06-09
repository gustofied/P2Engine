from __future__ import annotations

import json
from typing import Any, Dict, Tuple

from infra.evals.jinja_mixin import JinjaPromptMixin
from infra.evals.llm_eval import LLMEvaluator
from infra.evals.registry import evaluator
from infra.evals.rubric_library import get_rubric_text  # ← NEW
from services.services import ServiceContainer

_llm_client = ServiceContainer().get_llm_client()


class GPT4Judge(JinjaPromptMixin, LLMEvaluator):
    model = "openai/gpt-4o-mini"

    response_schema = {
        "type": "object",
        "properties": {
            "score": {"type": "number", "minimum": 0.0, "maximum": 1.0},
            "comment": {"type": "string"},
        },
        "required": ["score"],
        "additionalProperties": False,
    }

    # ------------------------------------------------------------------ #
    # Prompt construction
    # ------------------------------------------------------------------ #
    def build_messages(self, payload: Dict[str, Any]) -> list[dict]:
        # 1 — resolve rubric
        raw = payload.get("rubric")
        if raw and "\n" not in str(raw):
            # treat as *symbolic ID* → look up .jinja file
            try:
                rubric_txt = get_rubric_text(str(raw))
            except KeyError:
                # fall back to literal value if not found
                rubric_txt = str(raw)
        else:
            rubric_txt = str(raw or "Rate the final assistant answer for factual accuracy, " "completeness and clarity.")

        # 2 — summarise per-tool rewards (unchanged)
        traj = payload.get("traj", [])
        rewards: list[Tuple[str, float]] = []
        for msg in traj:
            if msg.get("role") != "tool":
                continue
            try:
                body = json.loads(msg.get("content", "{}"))
            except json.JSONDecodeError:
                continue
            r = body.get("reward")
            if r is not None:
                rewards.append((msg.get("name", "tool"), float(r)))

        # 3 — render system prompt
        sys_prompt = self._render_prompt(
            rubric=rubric_txt,
            score_type="float between 0.0 and 1.0",
            score_doc="0 = totally wrong / useless, 1 = perfect",
            extra_keys=True,
            template_version="v1.0.0",
        )
        if rewards:
            sys_prompt += "\n\nPer-tool rewards observed:\n" + "\n".join(f"- {n}: {v:.2f}" for n, v in rewards)

        return [{"role": "system", "content": sys_prompt}] + traj

    # ------------------------------------------------------------------ #
    # JSON parsing (unchanged)
    # ------------------------------------------------------------------ #
    def parse_result(self, raw: str) -> Tuple[float, Dict[str, float], str | None]:
        data = json.loads(raw)
        score = float(data["score"])
        comment = data.get("comment") or None
        metrics = {"has_comment": 1.0 if comment else 0.0}
        return score, metrics, comment


instance = GPT4Judge(_llm_client)


@evaluator(id="gpt4_judge", version="0.4")
def _entry(**payload: Any) -> Dict[str, Any]:
    return instance(dict(payload))
