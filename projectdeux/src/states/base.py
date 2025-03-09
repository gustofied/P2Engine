from abc import ABC, abstractmethod
from typing import TYPE_CHECKING
from src.custom_logging.central_logger import central_logger
from src.systems.event_system import Event
import uuid

if TYPE_CHECKING:
    from src.agents.base_agent import BaseAgent

class State(ABC):
    def __init__(self, agent: 'BaseAgent'):
        super().__init__()
        self.agent = agent

    @abstractmethod
    def transition_step(self) -> 'State':
        pass

    def on_enter(self):
        pass

    def on_exit(self):
        pass

class UserMessage(State):
    def __init__(self, agent: 'BaseAgent', message: str):
        super().__init__(agent)
        self.message = message

    def on_enter(self):
        central_logger.log_interaction(self.agent.name, "System", f"Processing user message: {self.message}")

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class AssistantMessage(State):
    def __init__(self, agent: 'BaseAgent', response: str):
        super().__init__(agent)
        if agent.parent:
            user_message_class = self.agent.state_registry.get_state_class("UserMessage")
            user_message_state = next(
                (state for state in self.agent.interaction_stack if isinstance(state, user_message_class)),
                None
            )
            if user_message_state:
                self.response = f"Completed task: {user_message_state.message}"
            else:
                self.response = "Task completed"
        else:
            self.response = response

    def on_enter(self):
        if self.agent.parent:
            self.agent.pending_events.append(Event("ResponseReadyEvent", self.response))
            central_logger.log_interaction(self.agent.name, "System", "Appended ResponseReadyEvent for sub-agent")
        else:
            user_message_class = self.agent.state_registry.get_state_class("UserMessage")
            user_message_state = next(
                (state for state in self.agent.interaction_stack if isinstance(state, user_message_class)),
                None
            )
            central_logger.log_interaction(
                self.agent.name, "System",
                f"Found UserMessage state: {user_message_state is not None}"
            )
            if user_message_state:
                original_message = user_message_state.message
                central_logger.log_interaction(
                    self.agent.name, "System",
                    f"Processing message: {original_message}"
                )
                user_message_lower = original_message.lower().strip()
                if "use test_tool" in user_message_lower:
                    correlation_id = str(uuid.uuid4())
                    self.agent.pending_events.append(Event(
                        "ToolCallEvent",
                        {"tool_name": "test_tool", "args": {}},
                        correlation_id
                    ))
                    central_logger.log_interaction(self.agent.name, "System", "Appended ToolCallEvent")
                elif "spawn" in user_message_lower:
                    parts = original_message.split(" ", 2)
                    if len(parts) == 3:
                        agent_type = parts[1]
                        task = parts[2]
                        correlation_id = str(uuid.uuid4())
                        self.agent.pending_events.append(Event(
                            "AgentCallEvent",
                            {"agent_type": agent_type, "task": task},
                            correlation_id
                        ))
                        central_logger.log_interaction(self.agent.name, "System", "Appended AgentCallEvent")
                    else:
                        self.agent.pending_events.append(Event("ClarificationEvent", "Incomplete spawn command"))
                        central_logger.log_interaction(self.agent.name, "System", "Appended ClarificationEvent for incomplete spawn")
                elif user_message_lower in ["hello", "hi", "hey"]:
                    self.agent.pending_events.append(Event("ResponseReadyEvent", "Hello! How can I assist you?"))
                    central_logger.log_interaction(self.agent.name, "System", "Appended ResponseReadyEvent for greeting")
                else:
                    self.agent.pending_events.append(Event("ClarificationEvent", "Unrecognized command"))
                    central_logger.log_interaction(self.agent.name, "System", "Appended ClarificationEvent for unrecognized command")
            if not self.agent.pending_events:
                self.agent.pending_events.append(Event("ResponseReadyEvent", self.response))
                central_logger.log_interaction(self.agent.name, "System", "Appended fallback ResponseReadyEvent")

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class Finished(State):
    def __init__(self, agent: 'BaseAgent', result: str = None):
        super().__init__(agent)
        self.result = result

    def on_enter(self):
        if self.agent.parent and self.result:
            self.agent.session.event_queue.publish(
                Event("AgentResultEvent", self.result, self.agent.correlation_id, source=self.agent.id)
            )
            central_logger.log_interaction(self.agent.name, "System", f"Published result to parent: {self.result}")

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class ClarificationState(State):
    def __init__(self, agent: 'BaseAgent'):
        super().__init__(agent)

    def on_enter(self):
        central_logger.log_interaction(self.agent.name, "System", "Entering ClarificationState: asking for clarification")
        self.agent.pending_events.append(Event("ResponseReadyEvent", "I didn’t understand that. Could you please rephrase?"))

    def transition_step(self):
        return None  # Transition handled by BaseAgent