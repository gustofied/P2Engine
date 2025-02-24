from dataclasses import dataclass, field
import uuid

@dataclass
class Entity:
    entity_type: str
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    components: dict = field(default_factory=dict)

    def add_component(self, component_name, component):
        self.components[component_name] = component

    def remove_component(self, component_name):
        self.components.pop(component_name, None)

    def get_component(self, component_name):
        return self.components.get(component_name)

    def __post_init__(self):
        print(f"[Entity] Created {self.entity_type} '{self.name}' with id: {self.id}")