from typing import List, Dict
from src.systems.base_system import BaseSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.agents.base_agent import BaseAgent
from src.event import Event

class GenericSystem(BaseSystem):
    def __init__(
        self,
        agents: List[BaseAgent],
        config_path: str,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        run_id: str
    ):
        super().__init__(
            agents=agents,
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=config,
            run_id=run_id,
            config_path=config_path
        )
        self.subscribe(self, "SpawnAgentEvent")

    def define_workflow(self) -> List[Dict]:
        task_sequence = self.config.get("task_sequence", [])
        if self.config.get("execution_type") == "asynchronous":
            for task in task_sequence:
                base_queue = task.get("queue", "default")
                task["queue"] = f"{base_queue}_{self.run_id}"
        return task_sequence

    def handle_event(self, event: Event):
        """Handle system-level events, such as spawning agents."""
        if event.type == "SpawnAgentEvent":
            agent_type = event.payload.get("agent_type", "default")
            parent_id = event.payload.get("parent_id")
            correlation_id = event.correlation_id
            parent = next((a for a in self.agents if a.id == parent_id), None) if parent_id else None
            self.spawn_agent(agent_type, parent, correlation_id)
            self.logger.log_interaction(
                "System", "GenericSystem",
                f"Spawned agent of type {agent_type} with correlation_id {correlation_id}",
                self.run_id
            )
        else:
            self.logger.log_interaction(
                "System", "GenericSystem",
                f"Unhandled event: {event.type}",
                self.run_id
            )