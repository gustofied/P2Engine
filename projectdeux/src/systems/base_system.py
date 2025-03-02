from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.custom_logging.central_logger import central_logger
from src.tasks.task_manager import TaskManager
from src.tasks.task_registry import TASK_REGISTRY
from src.tasks.async_task_manager import AsyncTaskManager

class BaseSystem(ABC):
    def __init__(
        self,
        agents,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        task_manager: Optional[TaskManager] = None,
        execution_type: str = "synchronous"
    ):
        self.agents = agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.config = config
        self.task_manager = task_manager or TaskManager()
        self.logger = central_logger
        self.goal = config.get("goal", "Solve a problem effectively")
        self.expected_result = config.get("expected_result", None)
        self.task_states: Dict[str, str] = {}
        self.system_type = self.__class__.__name__.lower().replace("system", "")
        self.execution_type = execution_type
        if self.execution_type == "asynchronous":
            self.async_task_manager = AsyncTaskManager()
        else:
            self.async_task_manager = None

    def get_agent_by_name(self, agent_name):
        """Retrieve an agent by name."""
        try:
            if isinstance(self.agents, dict):
                return self.agents.get(agent_name)
            return next(agent for agent in self.agents if agent.name == agent_name)
        except (StopIteration, AttributeError):
            return None

    def get_all_agents(self):
        """Return a list of all agent objects."""
        if isinstance(self.agents, dict):
            return list(self.agents.values())
        return self.agents

    @abstractmethod
    def define_workflow(self) -> List[Dict]:
        """Define the workflow."""
        pass

    def register_tasks(self):
        """Subclasses can override to register system-specific tasks."""
        pass

    def log_start(self, problem: str):
        """Log the start of the system run."""
        self.logger.log_system_start(
            system_name=self.__class__.__name__,
            entities=self.entity_manager.entities,
            problem=problem,
            goal=self.goal,
            expected_result=self.expected_result
        )

    def log_end(self, result: str, metadata: Dict, score: int):
        """Log the end of the system run."""
        all_agents = self.get_all_agents()
        self.logger.log_system_end(result, metadata, score, all_agents)

    def run_workflow(self, workflow: List[Dict]) -> Dict:
        """Execute the workflow based on execution_type."""
        if self.execution_type == "asynchronous":
            task_list = []
            for task_config in workflow:
                task_name = task_config["task_name"]
                args = task_config["args"]
                queue = task_config.get("queue", "default")
                task_func = TASK_REGISTRY[task_name]["function"]
                task_list.append((task_func, args, queue))
            async_result = self.async_task_manager.dispatch_workflow(task_list)
            final_result = self.async_task_manager.get_task_result(async_result, timeout=600)
            # Handle result flexibly
            if isinstance(final_result, tuple) and len(final_result) >= 4:
                result, all_logs, _, all_litellm_logs = final_result[:4]
            else:
                result = final_result  # Fallback to raw result
                all_logs = []
            for log in all_logs:
                self.logger.log_interaction(sender=log["from"], receiver=log["to"], message=log["message"])
            return {"final_result": result, "logs": all_logs}
        elif self.execution_type == "synchronous":
            results = {}
            for task_config in workflow:
                task_name = task_config["task_name"]
                agent_name = task_config["agent_name"]
                agent = self.get_agent_by_name(agent_name)
                if not agent:
                    raise ValueError(f"Agent '{agent_name}' not found.")
                if task_name not in self.task_manager.tasks:
                    self.task_manager.register_task(
                        task_name=task_name,
                        agents=[agent],
                        instruction=task_config["instruction"],
                        dependencies=task_config.get("dependencies", []),
                        required_params=task_config.get("required_params", []),
                        dependency_params=task_config.get("dependency_params", {})
                    )
                result = self.task_manager.execute_task(task_name, **task_config.get("params", {}))
                self.task_states[task_name] = self.task_manager.get_task_state(task_name)
                results[task_name] = result
            return results
        else:
            raise ValueError(f"Invalid execution type: {self.execution_type}")

    def run(self, **kwargs):
        """Execute the system's workflow."""
        self.log_start(kwargs.get("problem", "Unnamed problem"))
        self.register_tasks()
        workflow = self.define_workflow()
        results = self.run_workflow(workflow)
        self.log_end(str(results), metadata={"tasks": len(workflow)}, score=100)
        return results