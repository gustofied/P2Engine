"""
Tiny helper that gives evaluators a _render_prompt() method powered by Jinja2.
"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader, select_autoescape

_tpl_dir = Path(__file__).parent / "templates"
_env = Environment(
    loader=FileSystemLoader(_tpl_dir),
    autoescape=select_autoescape(),
    trim_blocks=True,
    lstrip_blocks=True,
)


class JinjaPromptMixin:
    """Add `_render_prompt(**ctx)` to render any template in infra/evals/templates"""

    tmpl_name: str = "judge_prompt.j2"

    def _render_prompt(self, **ctx) -> str:  
        tmpl = _env.get_template(self.tmpl_name)
        return tmpl.render(**ctx)
