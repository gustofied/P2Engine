# src/systems/base_system.py
from typing import List, Dict, Optional
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from custom_logging.central_logger import central_logger
from tasks.task_manager import TaskManager

class BaseSystem:
    def __init__(
        self,
        agents,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        task_manager: Optional[TaskManager] = None
    ):
        self.agents = agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.config = config
        self.task_manager = task_manager or TaskManager()
        self.logger = central_logger
        self.goal = config.get("goal", "Solve a problem effectively")
        self.expected_result = config.get("expected_result", None)
        # Track task states at the system level
        self.task_states: Dict[str, str] = {}

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
        self.logger.log_system_end(result, metadata, score)

    def run_workflow(self, tasks: List[Dict]) -> Dict:
        """Run a workflow of tasks, updating system-level task states."""
        results = {}
        for task_config in tasks:
            task_name = task_config["task_name"]
            agent_name = task_config["agent_name"]
            try:
                agent = next(a for a in self.agents if a.name == agent_name)
            except StopIteration:
                raise ValueError(f"Agent '{agent_name}' not found in system agents: {[a.name for a in self.agents]}")
            
            # Register task if not already registered
            if task_name not in self.task_manager.tasks:
                self.task_manager.register_task(
                    task_name=task_name,
                    agents=[agent],
                    instruction=task_config["instruction"],
                    dependencies=task_config.get("dependencies", []),
                    required_params=task_config.get("required_params", []),
                    dependency_params=task_config.get("dependency_params", {})
                )
            
            # Execute task and update system-level state
            result = self.task_manager.execute_task(task_name, **task_config.get("params", {}))
            self.task_states[task_name] = self.task_manager.get_task_state(task_name)
            results[task_name] = result

        return results

    def get_task_state(self, task_name: str) -> Optional[str]:
        """Get the state of a task, ensuring system awareness."""
        state = self.task_manager.get_task_state(task_name)
        if state:
            self.task_states[task_name] = state
        return state

    def list_task_states(self) -> Dict[str, str]:
        """List all task states known to the system."""
        return self.task_states.copy()

    def run(self, **kwargs):
        raise NotImplementedError("Subclasses must implement the run method")