from typing import TYPE_CHECKING, Optional, Dict
from src.states.state_registry import StateRegistry  # Updated to src.states
from src.custom_logging.central_logger import central_logger
from src.systems.event_system import Event
from celery_app import app as celery_app
from .base import State

if TYPE_CHECKING:
    from src.agents.base_agent import BaseAgent

class ToolCall(State):
    def __init__(self, agent: "BaseAgent", tool_name: str, args: dict, correlation_id: str):
        super().__init__(agent)
        self.tool_name = tool_name
        self.args = args
        self.correlation_id = correlation_id
        self.task = None

    def on_enter(self):
        try:
            if not hasattr(self.agent, 'session') or not self.agent.session:
                raise ValueError("Agent must have a session to execute tools")
            queue_name = f"tool_queue_{self.agent.session.run_id}"
            central_logger.log_interaction("ToolCall", "System", f"ToolCall run_id: {self.agent.session.run_id}")
            self.task = execute_tool_task.apply_async(
                args=(self.tool_name, self.args, self.correlation_id, self.agent.session.id),
                queue=queue_name,
                exchange=queue_name,
                routing_key=queue_name,
                retry=True,
                retry_policy={"max_retries": 3, "interval_start": 5}
            )
            self.agent.subscribe("ToolResultEvent", self.correlation_id)
            central_logger.log_interaction(
                self.agent.name, "System",
                f"Task queued: {self.task.id} to queue: {queue_name}"
            )
        except Exception as e:
            central_logger.log_interaction(self.agent.name, "System", f"ToolCall failed: {str(e)}")
            self.agent.pending_events.append(Event("ToolFailureEvent", {"error": str(e)}, correlation_id=self.correlation_id))

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class WaitingForToolResult(State):
    def __init__(self, agent: "BaseAgent", correlation_id: str, task=None):
        super().__init__(agent)
        self.correlation_id = correlation_id
        self.result = None
        self.task = task

    def handle_event(self, event: "Event"):
        if event.type == "ToolResultEvent" and event.correlation_id == self.correlation_id:
            self.result = event.payload
            central_logger.log_interaction(self.agent.name, "System", f"Received ToolResultEvent: {self.result}")

    def check_task(self):
        if self.task and self.task.ready():
            result = self.task.get()
            self.agent.pending_events.append(Event("ToolResultEvent", result["result"], self.correlation_id))
            self.agent.unsubscribe("ToolResultEvent", self.correlation_id)
            central_logger.log_interaction(self.agent.name, "System", f"Task completed: {result['result']}")

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class ToolResult(State):
    def __init__(self, agent: "BaseAgent", result: str):
        super().__init__(agent)
        self.result = result

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class AgentCall(State):
    def __init__(self, agent: "BaseAgent", agent_type: str, task: str, correlation_id: str):
        super().__init__(agent)
        self.agent_type = agent_type
        self.task = task
        self.correlation_id = correlation_id

    def on_enter(self):
        sub_agent = self.agent.session.spawn_agent(self.agent_type, parent=self.agent, correlation_id=self.correlation_id)
        sub_agent.process_event(Event("UserMessageEvent", self.task))
        central_logger.log_interaction(self.agent.name, "System", f"Spawned sub-agent with task: {self.task}")

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class WaitingForAgentResult(State):
    def __init__(self, agent: "BaseAgent", correlation_id: str):
        super().__init__(agent)
        self.correlation_id = correlation_id
        self.result = None

    def on_enter(self):
        self.agent.subscribe("AgentResultEvent", self.correlation_id)
        central_logger.log_interaction(self.agent.name, "System", f"Subscribed to AgentResultEvent with correlation_id: {self.correlation_id}")

    def handle_event(self, event: "Event"):
        if event.type == "AgentResultEvent" and event.correlation_id == self.correlation_id:
            self.result = event.payload
            central_logger.log_interaction(self.agent.name, "System", f"Received AgentResultEvent: {self.result}")

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class AgentResult(State):
    def __init__(self, agent: "BaseAgent", result: str):
        super().__init__(agent)
        self.result = result

    def transition_step(self):
        return None  # Transition handled by BaseAgent

@celery_app.task(bind=True)
def execute_tool_task(self, tool_name: str, args: dict, correlation_id: str, session_id: str, config_path: str = "scenario.yaml"):
    try:
        central_logger.log_interaction("Celery", "System", f"Task {self.request.id} started: tool={tool_name}")
        state_registry = StateRegistry(config_path)
        tool_class = state_registry.get_tool_class(tool_name)
        if not tool_class:
            raise ValueError(f"Tool '{tool_name}' not found in registry")
        tool = tool_class()
        result = tool.execute(**args)
        from src.systems.base_system import BaseSystem
        session = BaseSystem.session_instances.get(session_id)
        if session:
            session.event_queue.publish(Event("ToolResultEvent", result, correlation_id))
        return {"result": result, "task_id": self.request.id}
    except Exception as e:
        central_logger.log_interaction("Celery", "System", f"Task {self.request.id} failed: {str(e)}")
        raise