from dataclasses import dataclass
from typing import Any
from uuid import UUID

@dataclass
class Event:
    type: str
    payload: Any
    correlation_id: UUID

    def to_dict(self):
        return {
            "type": self.type,
            "payload": self.payload,
            "correlation_id": str(self.correlation_id)  # Convert UUID to str for serialization
        }