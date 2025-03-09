# projectdeux/src/systems/generic_system.py
from typing import List, Dict, Optional
from src.systems.base_system import BaseSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.tasks.task_manager import TaskManager
from src.custom_logging.central_logger import central_logger
from src.config.state_registry import StateRegistry
from src.agents.base_agent import BaseAgent

class GenericSystem(BaseSystem):
    def __init__(
        self,
        config_path: str,  # Path to scenario.yaml
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        run_id: str,
        task_manager: Optional[TaskManager] = None
    ):
        super().__init__(
            agents=[],
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=config,
            run_id=run_id,
            task_manager=task_manager,
            config_path=config_path  # Pass config_path to BaseSystem
        )
        # No need for this line anymore: self.state_registry = StateRegistry(config_path)

    def spawn_agent(self, name: str, parent: Optional["BaseAgent"] = None, correlation_id: Optional[str] = None):
        """Spawn a new agent with the state registry, parent, and correlation_id."""
        agent = BaseAgent(
            entity_manager=self.entity_manager,
            component_manager=self.component_manager,
            name=name,
            state_registry=self.state_registry,
            session=self
        )
        agent.parent = parent  # Set parent if provided
        agent.correlation_id = correlation_id  # Set correlation_id if provided
        self.agents.append(agent)
        return agent

    def define_workflow(self) -> List[Dict]:
        """Define a workflow based on the config's task sequence with dynamic queues."""
        task_sequence = self.config.get("task_sequence", [])
        if self.execution_type == "asynchronous":
            for task in task_sequence:
                base_queue = task.get("queue", "default")
                task["queue"] = f"{base_queue}_{self.run_id}"
        return task_sequence

    def tick(self):
        """Simulate one cycle of the event loop."""
        self.event_queue.dispatch()
        for agent in self.agents:
            agent.step()