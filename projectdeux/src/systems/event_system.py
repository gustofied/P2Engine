from __future__ import annotations
from typing import List, Optional, Dict, TYPE_CHECKING
from uuid import uuid4

# Instead of a top-level import:
# from agents.base_agent import BaseAgent
# Import BaseAgent only for type checking:
if TYPE_CHECKING:
    from src.agents.base_agent import BaseAgent

class Event:
    def __init__(self, event_type: str, payload: str, correlation_id: Optional[str] = None, source: Optional[str] = None):
        """Initialize an event with type, payload, and optional tracking attributes."""
        self.type = event_type
        self.payload = payload
        self.correlation_id = correlation_id or str(uuid4())  # Unique ID for tracking async operations
        self.source = source  # Originating agent or component

class EventQueue:
    def __init__(self):
        """Initialize the event queue and subscriber registry."""
        self.queue: List[Event] = []  # Queue to hold events
        self.subscribers: Dict[str, List["BaseAgent"]] = {}  # Mapping of event_type to list of agents

    def publish(self, event: Event):
        """Add an event to the queue for later dispatching."""
        self.queue.append(event)

    def subscribe(self, agent: "BaseAgent", event_type: str):
        """Register an agent to receive events of a specific type."""
        if event_type not in self.subscribers:
            self.subscribers[event_type] = []
        if agent not in self.subscribers[event_type]:
            self.subscribers[event_type].append(agent)

    def unsubscribe(self, agent: "BaseAgent", event_type: str):
        """Remove an agent's subscription to an event type."""
        if event_type in self.subscribers and agent in self.subscribers[event_type]:
            self.subscribers[event_type].remove(agent)

    def dispatch(self):
        """Process all queued events, notifying subscribed agents."""
        while self.queue:
            event = self.queue.pop(0)
            if event.type in self.subscribers:
                for agent in self.subscribers[event.type]:
                    agent.process_event(event)
