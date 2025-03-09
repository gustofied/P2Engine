from __future__ import annotations
from typing import Optional, List, Dict, TYPE_CHECKING
from collections import defaultdict
import uuid
import traceback
from src.entities.entity import Entity
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.integrations.llm.llm_client import LLMClient
from src.custom_logging.litellm_logger import my_custom_logging_fn
from src.custom_logging.central_logger import central_logger
from src.integrations.tools.base_tool import Tool
from src.systems.event_system import Event
from src.config.state_registry import StateRegistry

if TYPE_CHECKING:
    from src.systems.base_system import BaseSystem

class BaseAgent(Entity):
    # Transition table mapping (CurrentStateName, EventType) to NextStateName
    TRANSITIONS = {
        ("UserMessage", None): "AssistantMessage",
        ("AssistantMessage", "ResponseReadyEvent"): "Finished",
        ("AssistantMessage", "ToolCallEvent"): "ToolCall",
        ("ToolCall", None): "WaitingForToolResult",
        ("WaitingForToolResult", "ToolResultEvent"): "ToolResult",
        ("ToolResult", None): "AssistantMessage",
        ("AssistantMessage", "AgentCallEvent"): "AgentCall",
        ("AgentCall", None): "WaitingForAgentResult",
        ("WaitingForAgentResult", "AgentResultEvent"): "AgentResult",
        ("AgentResult", None): "AssistantMessage",
        # Error handling transitions
        ("ToolCall", "ToolFailureEvent"): "ErrorState",
        ("AgentCall", "AgentFailureEvent"): "ErrorState",
        ("ErrorState", "RetryEvent"): "AssistantMessage",
        ("ErrorState", "StopEvent"): "Finished",
        # Clarification transitions
        ("AssistantMessage", "ClarificationEvent"): "ClarificationState",
        ("ClarificationState", "UserMessageEvent"): "AssistantMessage",
    }

    def __init__(
        self,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        name: str,
        state_registry: StateRegistry,
        model: str = "openrouter/qwen/qwq-32b:free",
        api_key: Optional[str] = None,
        tools: Optional[List[Tool]] = None,
        system_prompt: str = "You are a helpful assistant",
        behaviors: Optional[Dict] = None,
        session: Optional["BaseSystem"] = None
    ):
        """Initialize the BaseAgent with necessary components and configurations."""
        super().__init__(entity_type="agent", name=name)
        self.model_name = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.behaviors = behaviors or {}
        self.tools = tools or []
        self.pending_events: List["Event"] = []
        self.interaction_stack: List["State"] = []
        self.session = session
        self.subscriptions = defaultdict(int)
        self.parent = None  # Reference to parent agent
        self.correlation_id = None  # ID to correlate sub-agent results
        self.state_registry = state_registry  # Store the registry
        self.retried = False  # Initialize retry flag to track retry attempts

        llm_client = LLMClient(model=self.model_name, api_key=self.api_key, logger_fn=my_custom_logging_fn)
        component_manager.attach_component(self, "model", client=llm_client)
        entity_manager.register(self)

    def process_event(self, event: "Event") -> None:
        """Handle incoming events by storing them or starting a state transition."""
        if event.type == "UserMessageEvent":
            user_message_class = self.state_registry.get_state_class("UserMessage")
            self.interaction_stack.append(user_message_class(self, event.payload))
            central_logger.log_interaction("EventQueue", self.name, f"Started UserMessage state for: {event.payload}")
        else:
            self.pending_events.append(event)
            central_logger.log_interaction("EventQueue", self.name, f"Received event: {event.type}")

    def step(self) -> None:
        """Process one pending event and transition the current state using the transition table."""
        if not self.interaction_stack:
            central_logger.log_interaction(self.name, "System", "No states in interaction_stack to process")
            return

        current_state = self.interaction_stack[-1]
        current_state_name = current_state.__class__.__name__

        # Log the state of the stack and events before processing
        central_logger.log_interaction(
            self.name, "System",
            f"Before step: stack={[s.__class__.__name__ for s in self.interaction_stack]}, "
            f"pending_events={[e.type for e in self.pending_events]}"
        )

        # Check for task completion if applicable
        if hasattr(current_state, 'check_task'):
            current_state.check_task()

        # Process the next event if available, removing it immediately
        event = self.pending_events.pop(0) if self.pending_events else None
        event_type = event.type if event else None
        central_logger.log_interaction(
            self.name, "System",
            f"Processing: state={current_state_name}, event={event_type}"
        )

        # Determine the next state from the transition table
        next_state_name = self.TRANSITIONS.get((current_state_name, event_type))
        if next_state_name:
            central_logger.log_interaction(
                self.name, "System",
                f"Expected transition: {current_state_name} -> {next_state_name} with event {event_type}"
            )
            try:
                next_state_class = self.state_registry.get_state_class(next_state_name)
                # Instantiate the next state based on its requirements
                if next_state_name == "ErrorState":
                    error_message = event.payload if event else "Unknown error"
                    next_state = next_state_class(self, error_message, failed_state=current_state)
                elif next_state_name == "Finished":
                    next_state = next_state_class(self, event.payload if event else None)
                elif next_state_name in ["ToolCall", "AgentCall"]:
                    correlation_id = event.correlation_id if event else str(uuid.uuid4())
                    if next_state_name == "ToolCall":
                        tool_name = event.payload.get("tool_name")
                        args = event.payload.get("args", {})
                        next_state = next_state_class(self, tool_name, args, correlation_id)
                    else:
                        agent_type = event.payload.get("agent_type")
                        task = event.payload.get("task")
                        next_state = next_state_class(self, agent_type, task, correlation_id)
                elif next_state_name == "WaitingForToolResult":
                    correlation_id = current_state.correlation_id if hasattr(current_state, "correlation_id") else str(uuid.uuid4())
                    task = getattr(current_state, "task", None)
                    next_state = next_state_class(self, correlation_id, task=task)
                elif next_state_name == "WaitingForAgentResult":
                    correlation_id = current_state.correlation_id if hasattr(current_state, "correlation_id") else str(uuid.uuid4())
                    next_state = next_state_class(self, correlation_id)
                elif next_state_name in ["ToolResult", "AgentResult"]:
                    next_state = next_state_class(self, event.payload)
                elif next_state_name == "UserMessage":
                    next_state = next_state_class(self, event.payload)
                elif next_state_name == "AssistantMessage":
                    if isinstance(current_state, (self.state_registry.get_state_class("ToolResult"), self.state_registry.get_state_class("AgentResult"))):
                        payload = current_state.result
                    else:
                        payload = "Processing..."
                    next_state = next_state_class(self, payload)
                else:
                    next_state = next_state_class(self)

                # Perform the transition
                self.interaction_stack.append(next_state)
                next_state.on_enter()
                central_logger.log_interaction(
                    self.name, "System",
                    f"Transition successful: {current_state_name} -> {next_state_name}"
                )
            except Exception as e:
                error_msg = f"Transition failed: {current_state_name} -> {next_state_name} with error: {str(e)}\n{traceback.format_exc()}"
                central_logger.log_interaction(self.name, "System", error_msg)
        else:
            central_logger.log_interaction(
                self.name, "System",
                f"No transition defined for state={current_state_name} with event={event_type}"
            )

    def subscribe(self, event_type: str, correlation_id: str = None) -> None:
        """Subscribe to an event type."""
        self.subscriptions[event_type] += 1
        if self.subscriptions[event_type] == 1:
            self.session.event_queue.subscribe(self, event_type)
        central_logger.log_interaction(self.name, "System", f"Subscribed to {event_type} with ID {correlation_id}")

    def unsubscribe(self, event_type: str, correlation_id: str = None) -> None:
        """Unsubscribe from an event type."""
        if event_type in self.subscriptions:
            self.subscriptions[event_type] -= 1
            if self.subscriptions[event_type] == 0:
                self.session.event_queue.unsubscribe(self, event_type)
                del self.subscriptions[event_type]
            central_logger.log_interaction(self.name, "System", f"Unsubscribed from {event_type} with ID {correlation_id}")

    def render_context(self) -> Dict:
        """Render the current context for LLM interactions."""
        history = [{"role": "system", "content": self.system_prompt}]
        user_message_class = self.state_registry.get_state_class("UserMessage")
        assistant_message_class = self.state_registry.get_state_class("AssistantMessage")
        for state in self.interaction_stack:
            if isinstance(state, user_message_class):
                history.append({"role": "user", "content": state.message})
            elif isinstance(state, assistant_message_class):
                history.append({"role": "assistant", "content": state.response})
        return {"agent_id": self.id, "history": history, "agent_name": self.name}

    @property
    def llm_client(self) -> LLMClient:
        """Access the LLM client component."""
        model_component = self.get_component("model")
        if model_component and hasattr(model_component, "client"):
            return model_component.client
        raise ValueError("Model component not found or invalid in BaseAgent")

    def interact(self, user_input: str) -> str:
        """Handle direct user interaction, including tool execution and LLM queries."""
        for tool in self.tools:
            if tool.__class__.__name__ == "WebScraperTool" and user_input.lower().startswith("scrape"):
                parts = user_input.split(" ", 2)
                if len(parts) == 3:
                    url, target = parts[1], parts[2]
                    return tool.execute(url=url, target=target)
                else:
                    return tool.execute(url=parts[1])

        messages = self._format_messages(user_input)
        metadata = {"agent_name": self.name, "agent_id": self.id, "system_prompt": self.system_prompt}
        try:
            response = self.llm_client.query(messages=messages, metadata=metadata)
            central_logger.log_interaction(self.name, "User", f"User input: {user_input}")
            central_logger.log_interaction(self.name, "System", f"Response: {response}")
            return response
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            central_logger.log_interaction(self.name, "System", error_msg)
            return error_msg

    def _format_messages(self, user_input: str) -> List[Dict]:
        """Format messages for LLM interaction based on behaviors."""
        formatter = self.behaviors.get("format_messages", lambda x: [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": x}
        ])
        return formatter(user_input)