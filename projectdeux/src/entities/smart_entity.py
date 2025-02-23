from abc import ABC, abstractmethod
from dataclasses import dataclass, field
import uuid

@dataclass
class SmartEntity(ABC):
    entity_type: str
    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    connectable: bool = True  # Indicates if this entity can form connections.
    connections: list = field(default_factory=list)  # List to hold connected entities.

    def __post_init__(self):
        print(f"[SmartEntity] Created {self.entity_type} '{self.name}' with id: {self.id}")

    @abstractmethod
    def interact(self, *args, **kwargs):
        """
        Abstract method for interaction.
        Entities like agents or tools should implement this.
        """
        pass
