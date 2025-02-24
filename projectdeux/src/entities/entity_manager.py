from .entity import Entity

class EntityManager:
    def __init__(self):
        self.entities = {}

    def register(self, entity: Entity):
        self.entities[entity.id] = entity
        print(f"[EntityManager] Registered {entity.entity_type} '{entity.name}' with id: {entity.id}")

    def lookup(self, entity_id: str):
        return self.entities.get(entity_id)

    def deregister(self, entity_id: str):
        if entity_id in self.entities:
            removed = self.entities.pop(entity_id)
            print(f"[EntityManager] Deregistered {removed.entity_type} '{removed.name}' with id: {entity_id}")
        else:
            print(f"[EntityManager] No entity found with id: {entity_id}")

    def list_entities(self):
        return list(self.entities.values())