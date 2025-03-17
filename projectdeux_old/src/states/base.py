from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Tuple, Dict
import uuid
from src.custom_logging.central_logger import central_logger
from src.event import Event
from src.redis_client import redis_client

if TYPE_CHECKING:
    from src.agents.base_agent import BaseAgent

class State(ABC):
    def __init__(self, agent: 'BaseAgent'):
        self.agent = agent

    @abstractmethod
    def transition_step(self) -> Tuple[str, Dict]:
        pass

    def on_enter(self):
        pass

    def on_exit(self):
        pass

    def to_dict(self) -> Dict:
        return {"type": self.__class__.__name__}

    @classmethod
    def from_dict(cls, data: Dict, agent: 'BaseAgent'):
        return cls(agent)

class UserMessage(State):
    def __init__(self, agent: 'BaseAgent', message: str):
        super().__init__(agent)
        self.message = message

    def on_enter(self):
        central_logger.log_interaction(
            self.agent.name, "System", f"Processing user message: {self.message}", self.agent.run_id
        )

    def transition_step(self) -> Tuple[str, Dict]:
        if "explore multiple options" in self.message.lower():
            branches = [
                {"task": "Option 1: Analyze A", "agent_name": "AnalyzerA"},
                {"task": "Option 2: Analyze B", "agent_name": "AnalyzerB"}
            ]
            correlation_id = str(uuid.uuid4())
            return "AgentCall", {"branches": branches, "correlation_id": correlation_id}
        else:
            response = self.agent.interact(self.message)
            return "AssistantMessage", {"response": response}

    def to_dict(self) -> Dict:
        return {"type": "UserMessage", "message": self.message}

    @classmethod
    def from_dict(cls, data: Dict, agent: 'BaseAgent'):
        return cls(agent, data["message"])

class AssistantMessage(State):
    def __init__(self, agent: 'BaseAgent', response: str):
        super().__init__(agent)
        self.response = response

    def on_enter(self):
        if self.agent.parent:
            event = Event("ResponseReadyEvent", self.response, correlation_id=self.agent.correlation_id)
            self.agent.session.publish(event)
            central_logger.log_interaction(
                self.agent.name, "System", "Published ResponseReadyEvent for sub-agent", self.agent.run_id
            )
        else:
            central_logger.log_interaction(
                self.agent.name, "System", f"Assistant response: {self.response}", self.agent.run_id
            )
            if self.agent.correlation_id:
                redis_client.set(f"response:{self.agent.correlation_id}", self.response)
                central_logger.log_interaction(
                    self.agent.name, "System", f"Stored response in Redis at response:{self.agent.correlation_id}", self.agent.run_id
                )

    def transition_step(self) -> Tuple[str, Dict]:
        return "Finished", {}

    def to_dict(self) -> Dict:
        return {"type": "AssistantMessage", "response": self.response}

    @classmethod
    def from_dict(cls, data: Dict, agent: 'BaseAgent'):
        return cls(agent, data["response"])

class Finished(State):
    def __init__(self, agent: 'BaseAgent', result: str = None):
        super().__init__(agent)
        self.result = result

    def on_enter(self):
        if self.agent.parent and self.result:
            event = Event("AgentResultEvent", self.result, correlation_id=self.agent.correlation_id, source=self.agent.id)
            self.agent.session.publish(event)
            central_logger.log_interaction(
                self.agent.name, "System", f"Published result to parent: {self.result}", self.agent.run_id
            )

    def transition_step(self) -> Tuple[str, Dict]:
        return None, {}

    def to_dict(self) -> Dict:
        return {"type": "Finished", "result": self.result}

    @classmethod
    def from_dict(cls, data: Dict, agent: 'BaseAgent'):
        return cls(agent, data["result"])

class ClarificationState(State):
    def __init__(self, agent: 'BaseAgent'):
        super().__init__(agent)

    def on_enter(self):
        central_logger.log_interaction(
            self.agent.name, "System", "Asking for clarification", self.agent.run_id
        )
        self.agent.session.publish(Event("ClarificationNeededEvent", "Please clarify your request."))

    def transition_step(self) -> Tuple[str, Dict]:
        return None, {}

    def to_dict(self) -> Dict:
        return {"type": "ClarificationState"}

    @classmethod
    def from_dict(cls, data: Dict, agent: 'BaseAgent'):
        return cls(agent)