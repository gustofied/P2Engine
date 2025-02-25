# systems/base_system.py
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from custom_logging.central_logger import central_logger

class BaseSystem:
    def __init__(self, agents, entity_manager: EntityManager, component_manager: ComponentManager):
        self.agents = agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.logger = central_logger
        self.default_goal = "Solve a problem effectively"  # Default goal at system level

    def log_start(self, problem: str, goal: str = None, expected_result: str = None):
        system_name = self.__class__.__name__
        goal = goal or self.default_goal  # Use provided goal or fallback to default
        self.logger.log_system_start(system_name, self.entity_manager.entities, problem, goal, expected_result)
        print(f"System '{system_name}' started with goal: {goal}")

    def log_end(self, result: str, evaluation: dict, reward: int):
        self.logger.log_system_end(result, evaluation, reward)
        print(f"System ended. Result: {result}, Reward: {reward}")

    def run(self, **kwargs):
        raise NotImplementedError("Subclasses must implement the run method")