from .base import State
from src.custom_logging.central_logger import central_logger
from src.systems.event_system import Event

class ToolFailureState(State):
    def __init__(self, agent, error_message, failed_state=None):
        super().__init__(agent)
        self.error_message = error_message
        self.failed_state = failed_state
        self.agent.retried = getattr(self.agent, 'retried', False)  # Initialize retry flag if not set

    def on_enter(self):
        failed_state_name = self.failed_state.__class__.__name__ if self.failed_state else "unknown"
        central_logger.log_interaction(
            self.agent.name, "System",
            f"Entered ToolFailureState: {self.error_message} from {failed_state_name}"
        )
        if not self.agent.retried:
            self.agent.retried = True
            self.agent.pending_events.append(Event("RetryEvent", None))
        else:
            self.agent.pending_events.append(Event("StopEvent", {"reason": "Failed after retry"}))

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class AgentFailureState(State):
    def __init__(self, agent, error_message, failed_state=None):
        super().__init__(agent)
        self.error_message = error_message
        self.failed_state = failed_state

    def on_enter(self):
        failed_state_name = self.failed_state.__class__.__name__ if self.failed_state else "unknown"
        central_logger.log_interaction(
            self.agent.name, "System",
            f"Entered AgentFailureState: {self.error_message} from {failed_state_name}"
        )
        self.agent.pending_events.append(Event("AgentFailureHandledEvent", {"error": self.error_message}))

    def transition_step(self):
        return None  # Transition handled by BaseAgent

class TimeoutState(State):
    def __init__(self, agent, timeout_reason):
        super().__init__(agent)
        self.timeout_reason = timeout_reason

    def on_enter(self):
        central_logger.log_interaction(
            self.agent.name, "System",
            f"Entered TimeoutState: {self.timeout_reason}"
        )
        self.agent.pending_events.append(Event("TimeoutHandledEvent", {"reason": self.timeout_reason}))

    def transition_step(self):
        return None  # Transition handled by BaseAgent