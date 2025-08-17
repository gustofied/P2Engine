from __future__ import annotations

import inspect
from typing import Any, Callable, Dict, Tuple

from infra.evals.loader import load_all as _load_evaluators
from infra.logging.logging_config import logger


class Evaluator:
    def __init__(
        self,
        evaluator_id: str,
        version: str,
        fn: Callable[..., Dict[str, Any]],
    ) -> None:
        self.id = evaluator_id
        self.version = version
        self.fn = fn
        self.signature = inspect.signature(fn)

    def __call__(self, *args, **kwargs) -> Dict[str, Any]:
        """
        Allow callers to invoke an evaluator with either style:

            evaluator(payload_dict)      # single positional dict
            evaluator(**payload_dict)    # expanded keyword-args

        without caring about the internal signature.
        """
        if args and kwargs:
            raise TypeError("Pass either a single payload dict *or* keyword-args, not both.")

        if len(args) == 1 and not kwargs:
            return self.fn(args[0]) 

        return self.fn(**kwargs)  

    def __repr__(self) -> str:
        return f"<Evaluator {self.id}@{self.version}>"


class _EvaluatorRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, Tuple[str, Evaluator]] = {}

    def register(
        self,
        evaluator_id: str,
        version: str,
        fn: Callable[..., Dict[str, Any]],
    ) -> Evaluator:
        if evaluator_id in self._registry:
            logger.warning(
                {
                    "message": "evaluator_redefined",
                    "evaluator_id": evaluator_id,
                    "old_version": self._registry[evaluator_id][0],
                    "new_version": version,
                }
            )
        eval_obj = Evaluator(evaluator_id, version, fn)
        self._registry[evaluator_id] = (version, eval_obj)
        logger.info(
            {
                "message": "evaluator_registered",
                "evaluator_id": evaluator_id,
                "version": version,
            }
        )
        return eval_obj

    def list_ids(self) -> list[str]:
        return sorted(self._registry.keys())

    def get(
        self,
        evaluator_id: str,
        *,
        version: str | None = None,
    ) -> Evaluator:
        if evaluator_id not in self._registry:
            _load_evaluators()

        try:
            registered_version, eval_obj = self._registry[evaluator_id]
        except KeyError as exc:  
            raise KeyError(
                f"Evaluator '{evaluator_id}' not found. " "Ensure its module is importable or the plug-in is installed."
            ) from exc

        if version is not None and version != registered_version:
            logger.warning(
                {
                    "message": "evaluator_version_mismatch",
                    "evaluator_id": evaluator_id,
                    "requested_version": version,
                    "available_version": registered_version,
                }
            )
        return eval_obj


registry = _EvaluatorRegistry()


def evaluator(id: str, version: str = "0.1"):
    """
    Decorator for easy registration:

        @evaluator("my_eval", version="1.2")
        def my_eval(payload): ...
    """

    def decorator(fn: Callable[..., Dict[str, Any]]):
        registry.register(id, version, fn)
        return fn

    return decorator
