from runtime.tasks.celery_app import app as celery_app


def get_task_context():
    ctx = getattr(celery_app, "dependencies", None)
    if ctx is not None:
        return ctx
    from infra.config_loader import agents
    from orchestrator.registries import tool_registry
    from services.services import ServiceContainer

    container = ServiceContainer()
    redis_client = container.get_redis_client()
    agent_factory = container.get_agent_factory()
    agent_registry = container.get_agent_registry()
    for ag_cfg in agents():
        agent = agent_factory.create(ag_cfg)
        agent_registry.register(agent, ag_cfg)
    celery_app.dependencies = {
        "redis_client": redis_client,
        "agent_registry": agent_registry,
        "tool_registry": tool_registry,
        "dedup_policy": container.get_dedup_policy(), 
    }
    return celery_app.dependencies
