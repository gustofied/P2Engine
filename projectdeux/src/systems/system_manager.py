from entities.entity import Entity
from custom_logging.central_logger import CentralLogger

class System:
    def __init__(self, name, logger: CentralLogger):
        self.name = name
        self.logger = logger

    def update(self, entities: dict):
        pass  # To be implemented by subclasses

class ToolUsageSystem(System):
    def __init__(self, logger: CentralLogger):
        super().__init__("tool_usage", logger)

    def update(self, entities: dict):
        for entity in entities.values():
            tool = entity.get_component("tool")
            if tool:
                message = f"{entity.name} is using tool: {tool.tool_name}"
                self.logger.log_interaction("System", entity.name, message)

class SystemManager:
    def __init__(self):
        self.systems = {}

    def add_system(self, system: System):
        self.systems[system.name] = system

    def remove_system(self, system_name: str):
        self.systems.pop(system_name, None)

    def update(self, entities: dict):
        for system in self.systems.values():
            system.update(entities)