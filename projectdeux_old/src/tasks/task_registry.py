from celery import shared_task
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.custom_logging.central_logger import central_logger
from src.redis_client import redis_client
from typing import TYPE_CHECKING, Any
import json
import os
import uuid
import time
from src.event import Event

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
    """Generic task that publishes an event and waits for the result asynchronously."""
    task_name = task_config["task_name"]
    instruction = task_config["instruction"]
    params_config = task_config.get("params", {})
    run_id = scenario_data.get("run_id", "unknown_run_id") if scenario_data else "unknown_run_id"

    if previous_output is None:
        scenario_data = scenario_data or {"context": {}, "run_params": {}, "run_id": run_id}
    else:
        _, scenario_data = previous_output

    params = {k: resolve_param(v, scenario_data) for k, v in params_config.items()}
    user_input = instruction.format(**params)
    central_logger.log_interaction("System", "generic_task", f"Generated user input: {user_input}", run_id)

    from src.systems.base_system import BaseSystem
    agent_name = task_config.get("agent_name")
    system = BaseSystem.session_instances.get(scenario_data["run_id"])
    if not system:
        central_logger.log_interaction("System", "generic_task", f"System for run_id '{run_id}' not found", run_id)
        return ("System not found", scenario_data)

    agent = system.get_agent_by_name(agent_name)
    if not agent:
        central_logger.log_interaction("System", "generic_task", f"Agent '{agent_name}' not found", run_id)
        return ("Agent not found", scenario_data)

    correlation_id = str(uuid.uuid4())
    event = Event("UserMessageEvent", user_input, correlation_id=correlation_id)
    central_logger.log_interaction("System", "generic_task", f"Publishing event with correlation_id: {correlation_id}", run_id)
    
    try:
        system.publish(event)
    except Exception as e:
        central_logger.log_error("System", e, run_id, context={"action": "publish_event", "event_type": event.type})
        return (f"Error publishing event: {str(e)}", scenario_data)

    # Wait for the response in Redis
    max_wait = task_config.get("timeout", 30)  # Default to 30 seconds, configurable via task_config
    start_time = time.time()
    while time.time() - start_time < max_wait:
        response = redis_client.get(f"response:{correlation_id}")
        if response:
            result = response.decode()
            break
        time.sleep(0.5)
    else:
        result = f"Timeout waiting for response after {max_wait} seconds"

    scenario_data["context"].setdefault(task_name, []).append({"agent": agent_name, "output": result})
    central_logger.log_interaction("System", agent_name, f"Executed {task_name}: {result}", run_id)
    return (result, scenario_data)

@shared_task
def write_artifact(storage_file: str, key: str, value: Any, run_id: str) -> None:
    """Write a key-value pair to a JSON artifact file asynchronously."""
    try:
        if os.path.exists(storage_file):
            with open(storage_file, 'r') as f:
                store = json.load(f)
        else:
            store = {}
        store[key] = value
        with open(storage_file, 'w') as f:
            json.dump(store, f, indent=2)
        central_logger.log_interaction("ArtifactWriteTask", "System", f"Wrote key '{key}' to {storage_file}", run_id)
    except Exception as e:
        central_logger.log_interaction("ArtifactWriteTask", "System", f"Failed to write key '{key}' to {storage_file}: {str(e)}", run_id)

from src.tasks.task_definitions import process_agent_step, process_branch_task, process_agent_event

TASK_REGISTRY = {
    "generic_task": {"function": generic_task},
    "write_artifact": {"function": write_artifact},
    "process_agent_step": {"function": process_agent_step},
    "process_branch_task": {"function": process_branch_task},
    "process_agent_event": {"function": process_agent_event},
}