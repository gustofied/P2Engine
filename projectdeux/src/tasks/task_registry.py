# src/tasks/task_registry.py
from celery import shared_task
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.custom_logging.central_logger import central_logger
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.agents.base_agent import BaseAgent

def resolve_param(param_value, scenario_data):
    """Resolve parameter values from run_params or context, handling non-string values."""
    if not isinstance(param_value, str):
        return param_value
    if param_value.startswith("run_params."):
        key = param_value.split(".", 1)[1]
        return scenario_data.get("run_params", {}).get(key, "")
    elif param_value.startswith("context."):
        keys = param_value.split(".")[1:]
        value = scenario_data.get("context", {})
        for key in keys:
            value = value.get(key, {})
        if isinstance(value, list):
            outputs = [item["output"] for item in value if "output" in item]
            return ", ".join(outputs)
        return str(value)
    return param_value

@shared_task
def generic_task(previous_output, agent_system_prompt, task_config, scenario_data=None):
    """Generic task that executes any instruction based on task_config."""
    task_name = task_config["task_name"]
    instruction = task_config["instruction"]
    params_config = task_config.get("params", {})

    if previous_output is None:
        scenario_data = scenario_data or {"context": {}, "run_params": {}}
    else:
        _, scenario_data = previous_output

    # Local import to break circular dependency.
    from src.agents.base_agent import BaseAgent

    entity_manager = EntityManager()
    component_manager = ComponentManager()
    agent = BaseAgent(
        entity_manager=entity_manager,
        component_manager=component_manager,
        name=task_config.get("agent_name", "TempAgent"),
        system_prompt=agent_system_prompt
    )

    params = {k: resolve_param(v, scenario_data) for k, v in params_config.items()}
    user_input = instruction.format(**params)

    result = agent.interact(user_input)

    scenario_data["context"].setdefault(task_name, []).append({"agent": agent.name, "output": result})
    central_logger.log_interaction("System", agent.name, f"Executed {task_name}: {result}")

    return (result, scenario_data)

TASK_REGISTRY = {
    "generic_task": {"function": generic_task}
}
