import importlib
import os
from infra.logging.logging_config import logger
from orchestrator.registries import tool_registry

# cache to avoid duplicate INFO spam in repeated invocations
_MOD_CACHE: set[str] = set()


def load_tools() -> None:
    """
    Dynamically import every Python file in `tools/` once.
    Re-invocations are cheap (noisy INFO → DEBUG).
    """
    tools_dir = os.path.dirname(__file__)

    for filename in os.listdir(tools_dir):
        if not filename.endswith(".py") or filename == "__init__.py":
            continue

        module_name = filename[:-3]  # strip ".py"

        if module_name in _MOD_CACHE:
            logger.debug("Imported tool module: %s (cached)", module_name)
            continue

        try:
            importlib.import_module(f".{module_name}", package="tools")
            logger.info("Imported tool module: %s", module_name)
            _MOD_CACHE.add(module_name)
        except Exception as exc:
            logger.error("Error importing tool module %s: %s", module_name, exc)

    logger.info("Registered tools: %s", list(tool_registry._tools.keys()))


# Initial import pass
load_tools()

__all__ = ["tool_registry"]
