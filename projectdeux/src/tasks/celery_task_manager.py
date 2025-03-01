# projectdeux/src/tasks/celery_task_manager.py

from typing import List, Dict
from celery.result import AsyncResult
from celery_app import app
from src.custom_logging.central_logger import central_logger
from src.tasks.celery_tasks import TASK_REGISTRY  # Import the registry

class CeleryTaskManager:
    """
    A TaskManager that dispatches tasks to specific Celery queues based on agent_name,
    using configurations provided at initialization.
    """
    def __init__(self, agent_configs: List[Dict]):
        # Dynamically build agent-to-queue mappings from the provided config
        self.agent_queues = {agent["name"]: agent["queue"] for agent in agent_configs}
        self.task_states = {}

    def execute_task(self, task_name: str, agent_name: str, scenario_data=None, **kwargs):
        """
        Dispatch the named task to Celery using the TASK_REGISTRY.
        Uses the assigned agent's queue or falls back to 'default'.
        """
        queue_name = self.agent_queues.get(agent_name, "default")

        # Get the task function from TASK_REGISTRY
        task_func = TASK_REGISTRY.get(task_name)
        if not task_func:
            raise ValueError(f"Task '{task_name}' not found in TASK_REGISTRY")

        # Prepare arguments for the task
        # Assuming tasks follow a pattern: task(agent_id, **kwargs)
        # Adjust based on actual task signatures if needed
        task_args = [agent_name]  # Assuming agent_id is agent_name; adjust if needed
        task_kwargs = {**kwargs, "scenario_data": scenario_data}

        # Apply the task asynchronously
        result_async = task_func["function"].apply_async(
            args=task_args,
            kwargs=task_kwargs,
            queue=queue_name
        )
        self.task_states[task_name] = "queued"
        central_logger.log_interaction(
            sender="CeleryTaskManager",
            receiver="System",
            message=f"{task_name} queued. ID={result_async.id}, Agent={agent_name}, Queue={queue_name}"
        )
        return f"{task_name} queued (ID={result_async.id})"

    def get_task_result(self, task_id: str):
        """
        Retrieve the result of a task by its ID.
        """
        async_res = AsyncResult(task_id, app=app)
        if async_res.ready():
            return async_res.result
        return f"Task {task_id} not finished. Status={async_res.status}"
