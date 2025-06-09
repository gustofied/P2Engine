import os  # ⬅ added
from pathlib import Path

from infra import config_loader as cfg
from infra.artifacts.bus import ArtifactBus
from infra.config import BASE_DIR
from infra.logging.logging_config import logger
from orchestrator.registries import tool_registry
from runtime.tasks.celery_app import app as celery_app
from services.services import ServiceContainer


def main() -> None:
    logger.info("Starting single-pass global initialization...")
    container = ServiceContainer()
    redis_client = container.get_redis_client()
    agent_factory = container.get_agent_factory()
    agent_registry = container.get_agent_registry()

    # Artifacts now drop right next to run logs if LOG_DIR is set
    ArtifactBus.get_instance(
        redis_client=redis_client,
        base_dir=Path(os.getenv("LOG_DIR", BASE_DIR)),
    )

    for agent_cfg in cfg.agents():
        agent = agent_factory.create(agent_cfg)
        agent_registry.register(agent, agent_cfg)

    celery_app.dependencies = {
        "redis_client": redis_client,
        "agent_registry": agent_registry,
        "tool_registry": tool_registry,
        "dedup_policy": container.get_dedup_policy(),
    }
    logger.info("Global init done. Tools: %s", list(tool_registry._tools.keys()))


if __name__ == "__main__":
    main()
