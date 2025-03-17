from __future__ import annotations
from typing import Optional, List, Dict, TYPE_CHECKING
import uuid
import json
import traceback
from src.entities.entity import Entity
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.integrations.llm.llm_client import LLMClient
from src.custom_logging.central_logger import central_logger
from src.integrations.tools.base_tool import Tool
from src.states.state_registry import StateRegistry
from src.states.base import State, UserMessage, AssistantMessage, ClarificationState
from src.states.advanced import AgentCall, WaitingForAgentResult, AgentResult, ToolCall
from src.states.error_states import ToolFailureState, AgentFailureState, TimeoutState
from src.states.transition_table import TRANSITIONS
from src.redis_client import redis_client
from src.event import Event

if TYPE_CHECKING:
    from src.systems.base_system import BaseSystem

class BaseAgent(Entity):
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
        session: Optional["BaseSystem"] = None,
        run_id: Optional[str] = None
    ):
        super().__init__(entity_type="agent", name=name)
        self.model_name = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.behaviors = behaviors or {}
        self.tools = tools or []
        self.interaction_stack: List["State"] = []
        self.session = session
        self.run_id = run_id if run_id else session.run_id if session else "no_session"
        self.parent = None
        self.correlation_id = None
        self.state_registry = state_registry
        self.state_changed = False  # Track if state needs saving

        llm_client = LLMClient(model=self.model_name, api_key=self.api_key, logger_fn=central_logger.log_interaction)
        component_manager.attach_component(self, "model", client=llm_client)
        entity_manager.register(self)

        if self.session and hasattr(self.session, 'artifact_store'):
            for tool in self.tools:
                if hasattr(tool, 'set_artifact_store'):
                    tool.set_artifact_store(self.session.artifact_store)

    def save_state(self):
        if not self.state_changed:
            return  # Skip if no changes
        state = {"interaction_stack": [state.to_dict() for state in self.interaction_stack]}
        redis_client.set(f"agent_state:{self.id}", json.dumps(state))
        central_logger.log_interaction(
            self.name, "System", f"Saved agent state: stack_size={len(self.interaction_stack)}", self.run_id
        )
        self.state_changed = False

    def load_state(self):
        state_str = redis_client.get(f"agent_state:{self.id}")
        if state_str:
            try:
                state = json.loads(state_str)
                self.interaction_stack = [
                    self.state_registry.get_state_class(s["type"]).from_dict(s, self)
                    for s in state["interaction_stack"]
                ]
                central_logger.log_interaction(
                    self.name, "System", f"Loaded agent state: stack_size={len(self.interaction_stack)}", self.run_id
                )
            except KeyError as e:
                central_logger.log_interaction(
                    self.name, "System", f"State class not found: {str(e)}", self.run_id
                )
                self.interaction_stack = []
        else:
            self.interaction_stack = []
            central_logger.log_interaction(
                self.name, "System", "No state found in Redis; initialized empty stack", self.run_id
            )

    def process_event(self, event: "Event") -> None:
        if event is None:
            return
        if event.type == "UserMessageEvent":
            self.correlation_id = event.correlation_id
            self.interaction_stack.append(UserMessage(self, event.payload))
            self.state_changed = True
            central_logger.log_interaction("System", self.name, f"Started UserMessage state for: {event.payload}", self.run_id)
        else:
            self.step(event)

    def step(self, event: Optional["Event"] = None) -> None:
        if not self.interaction_stack:
            return
        current_state = self.interaction_stack[-1]
        current_state_name = current_state.__class__.__name__
        event_type = event.type if event else None

        central_logger.log_interaction(
            self.name, "System",
            f"Processing state: {current_state_name} with event {event_type}",
            self.run_id
        )

        if event_type == "ClarificationNeededEvent":
            next_state = ClarificationState(self)
            self.interaction_stack.append(next_state)
            self.state_changed = True
            next_state.on_enter()
            return

        if hasattr(current_state, 'check_task'):
            current_state.check_task()

        if event_type == "AgentResultEvent" and event.correlation_id:
            self._aggregate_branch_result(event)
            return

        if event_type == "ToolCallEvent":
            tool_name = event.payload.get("tool_name")
            args = event.payload.get("args", {})
            correlation_id = event.correlation_id or str(uuid.uuid4())
            next_state = ToolCall(self, tool_name, args, correlation_id)
            self.interaction_stack.append(next_state)
            self.state_changed = True
            next_state.on_enter()
            return

        if event_type is None:
            result = current_state.transition_step()
            if isinstance(result, tuple):
                next_state_name, args = result
            else:
                next_state_name, args = result, {}
        else:
            next_state_name = TRANSITIONS.get((current_state_name, event_type))
            args = {}

        if next_state_name:
            try:
                next_state_class = self.state_registry.get_state_class(next_state_name)
                if next_state_name == "AssistantMessage":
                    response = args.get("response", "Default response")
                    next_state = AssistantMessage(self, response)
                elif next_state_name == "ClarificationState":
                    next_state = ClarificationState(self)
                elif next_state_name == "AgentCall" and event_type == "AgentCallEvent":
                    agent_type = event.payload.get("agent_type", "Analyzer")
                    task = event.payload.get("task", "Explore options")
                    correlation_id = event.correlation_id or str(uuid.uuid4())
                    next_state = AgentCall(self, [{"task": task, "agent_name": agent_type}], correlation_id)
                elif next_state_name == "WaitingForAgentResult":
                    correlation_id = current_state.correlation_id if hasattr(current_state, "correlation_id") else str(uuid.uuid4())
                    next_state = WaitingForAgentResult(self, correlation_id)
                elif next_state_name == "AgentResult":
                    next_state = AgentResult(self, event.payload)
                else:
                    next_state = next_state_class(self, **args)

                self.interaction_stack.append(next_state)
                self.state_changed = True
                next_state.on_enter()
                central_logger.log_interaction(
                    self.name, "System",
                    f"Transition successful: {current_state_name} -> {next_state_name}",
                    self.run_id
                )
            except Exception as e:
                central_logger.log_interaction(
                    self.name, "System",
                    f"Transition failed: {str(e)}\n{traceback.format_exc()}",
                    self.run_id
                )
        else:
            central_logger.log_interaction(
                self.name, "System",
                f"No transition for {current_state_name} with {event_type}",
                self.run_id
            )

    def _aggregate_branch_result(self, event: "Event") -> None:
        result = event.payload
        self.interaction_stack.append(AgentResult(self, result))
        self.state_changed = True
        self.step()

    def subscribe(self, event_type: str, correlation_id: Optional[str] = None) -> None:
        if self.session:
            self.session.subscribe(self, event_type, correlation_id)
            central_logger.log_interaction(self.name, "System", f"Subscribed to {event_type}", self.run_id)

    def unsubscribe(self, event_type: str) -> None:
        if self.session:
            self.session.unsubscribe(self, event_type)
            central_logger.log_interaction(self.name, "System", f"Unsubscribed from {event_type}", self.run_id)

    def render_context(self) -> Dict:
        history = [{"role": "system", "content": self.system_prompt}]
        for state in self.interaction_stack:
            if isinstance(state, UserMessage):
                history.append({"role": "user", "content": state.message})
            elif isinstance(state, AssistantMessage):
                history.append({"role": "assistant", "content": state.response})
        return {"agent_id": self.id, "history": history, "agent_name": self.name}

    @property
    def llm_client(self) -> LLMClient:
        model_component = self.get_component("model")
        if model_component and hasattr(model_component, "client"):
            return model_component.client
        raise ValueError("Model component not found or invalid")

    def interact(self, user_input: str) -> str:
        """Synchronous fallback; prefer state machine for async operations."""
        for tool in self.tools:
            if tool.__class__.__name__ == "TestTool" and "test_tool" in user_input.lower():
                return tool.execute(message=user_input)
            elif tool.__class__.__name__ == "WebScraperTool" and user_input.lower().startswith("scrape"):
                parts = user_input.split(" ", 2)
                return tool.execute(url=parts[1], target=parts[2]) if len(parts) == 3 else tool.execute(url=parts[1])
        messages = self._format_messages(user_input)
        metadata = {"agent_name": self.name, "agent_id": self.id, "system_prompt": self.system_prompt}
        try:
            response = self.llm_client.query(messages=messages, metadata=metadata)
            central_logger.log_interaction(self.name, "User", f"User input: {user_input}", self.run_id)
            central_logger.log_interaction(self.name, "System", f"Response: {response}", self.run_id)
            return response
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            central_logger.log_interaction(self.name, "System", error_msg, self.run_id)
            return error_msg

    def _format_messages(self, user_input: str) -> List[Dict]:
        formatter = self.behaviors.get("format_messages", lambda x: [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": x}
        ])
        return formatter(user_input)