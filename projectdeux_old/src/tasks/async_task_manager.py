from celery import chain
from celery.result import AsyncResult
from typing import List, Dict, Tuple, Callable
from src.custom_logging.central_logger import central_logger
from src.tasks.task_registry import TASK_REGISTRY

class AsyncTaskManager:
    def __init__(self, run_id: str):
        """Initialize with the global task registry, logger, and run_id."""
        self.task_registry = TASK_REGISTRY
        self.logger = central_logger
        self.run_id = run_id

    def dispatch_task(self, task_name: str, args: list, kwargs: dict, queue: str = "default") -> AsyncResult:
        """Dispatch a single task to a specified queue."""
        task_func = self.task_registry[task_name]["function"]
        async_result = task_func.apply_async(args=args, kwargs=kwargs, queue=queue)
        self.logger.log_interaction(
            "AsyncTaskManager", "System", 
            f"Dispatched task: {task_name} to queue: {queue}, Task ID: {async_result.id}", 
            self.run_id
        )
        return async_result

    def dispatch_workflow(self, task_list: List[Tuple[Callable, List, str]]) -> AsyncResult:
        """Dispatch a chain of tasks (workflow) to run sequentially."""
        celery_tasks = []
        for i, (task_func, args, queue) in enumerate(task_list):
            task = task_func.s(*args).set(queue=queue)
            celery_tasks.append(task)
        full_chain = chain(*celery_tasks)
        async_result = full_chain()
        self.logger.log_interaction(
            "AsyncTaskManager", "System", 
            f"Dispatched workflow, Task ID: {async_result.id}", 
            self.run_id
        )
        return async_result

    def get_task_result(self, async_result: AsyncResult, timeout: int = 120):
        """Retrieve the result of a task or workflow with a timeout."""
        try:
            result = async_result.get(timeout=timeout)
            self.logger.log_interaction(
                "AsyncTaskManager", "System", 
                f"Got result: {result}", 
                self.run_id
            )
            return result
        except Exception as e:
            self.logger.log_interaction(
                "AsyncTaskManager", "System", 
                f"Error getting result: {e}", 
                self.run_id
            )
            raise