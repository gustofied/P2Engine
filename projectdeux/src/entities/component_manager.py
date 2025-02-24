from .entity import Entity

class Component:
    def __init__(self, name):
        self.name = name

class ToolComponent(Component):
    def __init__(self, tool_name):
        super().__init__("tool")
        self.tool_name = tool_name

class ConnectionComponent(Component):
    def __init__(self, target_entity_id):
        super().__init__("connection")
        self.target_entity_id = target_entity_id

class MemoryComponent(Component):
    def __init__(self):
        super().__init__("memory")
        self.history = []

    def add_to_history(self, message):
        self.history.append(message)

class ComponentManager:
    def __init__(self):
        self.component_types = {
            "tool": ToolComponent,
            "connection": ConnectionComponent,
            "memory": MemoryComponent  # New component type
        }

    def create_component(self, component_type, **kwargs):
        component_class = self.component_types.get(component_type)
        if component_class:
            return component_class(**kwargs)
        raise ValueError(f"Unknown component type: {component_type}")

    def attach_component(self, entity: Entity, component_type: str, **kwargs):
        component = self.create_component(component_type, **kwargs)
        entity.add_component(component.name, component)