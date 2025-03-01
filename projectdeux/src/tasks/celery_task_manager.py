# projectdeux/src/tasks/celery_task_manager.py

from typing import List, Dict
from celery.result import AsyncResult
from celery_app import app
from src.custom_logging.central_logger import central_logger
from src.tasks.celery_tasks import scrape_task, summarize_task, plan_research

class CeleryTaskManager:
    """
    A TaskManager that dispatches tasks to specific Celery queues based on agent_name,
    using configurations provided at initialization.
    """
    def __init__(self, agent_configs: List[Dict]):
        # Dynamically build agent-to-queue mappings from the provided config
        self.agent_queues = {agent["name"]: agent["queue"] for agent in agent_configs}
        self.tasks = {}
        self.task_states = {}

    def register_task(self, task_name: str, description: str = "", **kwargs):
        self.tasks[task_name] = {
            "description": description,
            "extra": kwargs
        }
        self.task_states[task_name] = "registered"

    def execute_task(self, task_name: str, agent_name: str, scenario_data=None, **kwargs):
        """
        Dispatch the named task to Celery, using the assigned agent's queue.
        Falls back to 'default' queue if agent is unknown.
        """
        queue_name = self.agent_queues.get(agent_name, "default")

        if task_name == "scrape":
            result_async = scrape_task.apply_async(
                args=[kwargs["url"], kwargs.get("target", "p")],
                kwargs={"scenario_data": scenario_data},
                queue=queue_name
            )
            self.task_states[task_name] = "queued"
            central_logger.log_interaction(
                sender="CeleryTaskManager",
                receiver="System",
                message=f"Scrape queued. ID={result_async.id}, Agent={agent_name}, Queue={queue_name}"
            )
            return f"ScrapeTask queued (ID={result_async.id})"

        elif task_name == "summarize":
            result_async = summarize_task.apply_async(
                args=[kwargs["text"]],
                kwargs={"scenario_data": scenario_data},
                queue=queue_name
            )
            self.task_states[task_name] = "queued"
            central_logger.log_interaction(
                sender="CeleryTaskManager",
                receiver="System",
                message=f"Summarize queued. ID={result_async.id}, Agent={agent_name}, Queue={queue_name}"
            )
            return f"SummarizeTask queued (ID={result_async.id})"

        elif task_name == "plan_research":
            result_async = plan_research.apply_async(
                args=[kwargs["domain"]],
                kwargs={"scenario_data": scenario_data},
                queue=queue_name
            )
            self.task_states[task_name] = "queued"
            central_logger.log_interaction(
                sender="CeleryTaskManager",
                receiver="System",
                message=f"Plan_research queued. ID={result_async.id}, Agent={agent_name}, Queue={queue_name}"
            )
            return f"PlanResearch queued (ID={result_async.id})"

        else:
            return f"Unknown task: {task_name}"

    def get_task_result(self, task_id: str):
        async_res = AsyncResult(task_id, app=app)
        if async_res.ready():
            return async_res.result
        return f"Task {task_id} not finished. Status={async_res.status}"