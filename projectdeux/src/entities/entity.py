from dataclasses import dataclass, field
import uuid
import logging

logger = logging.getLogger(__name__)

@dataclass
class Entity:
    entity_type: str
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    components: dict = field(default_factory=dict)

    def add_component(self, component_name: str, component: object) -> None:
        self.components[component_name] = component
        logger.debug(f"Added component '{component_name}' to {self.entity_type} '{self.name}' (ID: {self.id})")

    def remove_component(self, component_name: str) -> None:
        if component_name in self.components:
            del self.components[component_name]
            logger.debug(f"Removed component '{component_name}' from {self.entity_type} '{self.name}' (ID: {self.id})")

    def get_component(self, component_name: str):
        return self.components.get(component_name)

    def __post_init__(self):
        logger.info(f"Created {self.entity_type} '{self.name}' with id: {self.id}")
