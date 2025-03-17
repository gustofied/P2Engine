from typing import TYPE_CHECKING, List, Dict, Tuple
from src.custom_logging.central_logger import central_logger
from celery_app import app as celery_app
from .base import State
from src.event import Event
from redis_client import redis_client

if TYPE_CHECKING:
    from src.agents.base_agent import BaseAgent

class ToolCall(State):
    def __init__(self, agent: "BaseAgent", tool_name: str, args: dict, correlation_id: str):
        super().__init__(agent)
        self.tool_name = tool_name
        self.args = args
        self.correlation_id = correlation_id
        self.task_id = None

    def on_enter(self):
        try:
            queue_name = f"tool_queue_{self.agent.run_id}"
            task = celery_app.send_task(
                "src.tasks.task_definitions.execute_tool_task",
                args=[self.tool_name, self.args, self.agent.run_id],
                queue=queue_name
            )
            self.task_id = task.id
            redis_client.set(f"tool_task:{self.correlation_id}", task.id)
            central_logger.log_interaction(
                self.agent.name, "System", f"ToolCall initiated: {self.tool_name}, Task ID: {task.id}", self.agent.run_id
            )
            self.agent.interaction_stack.append(WaitingForToolResult(self.agent, self.correlation_id, task_id=self.task_id))
        except Exception as e:
            central_logger.log_interaction(
                self.agent.name, "System", f"ToolCall failed: {str(e)}", self.agent.run_id
            )
            self.agent.session.publish(Event("ToolFailureEvent", {"error": str(e)}, self.correlation_id))

    def transition_step(self):
        return None, {}

    def to_dict(self):
        return {
            "type": "ToolCall",
            "tool_name": self.tool_name,
            "args": self.args,
            "correlation_id": self.correlation_id,
            "task_id": self.task_id
        }

    @classmethod
    def from_dict(cls, data: dict, agent: "BaseAgent"):
        instance = cls(agent, data["tool_name"], data["args"], data["correlation_id"])
        instance.task_id = data.get("task_id")
        return instance

class WaitingForToolResult(State):
    def __init__(self, agent: "BaseAgent", correlation_id: str, task_id: str = None):
        super().__init__(agent)
        self.correlation_id = correlation_id
        self.task_id = task_id

    def check_task(self):
        if self.task_id:
            result = celery_app.AsyncResult(self.task_id)
            if result.ready():
                try:
                    tool_result = result.get()
                    redis_client.set(f"tool_result:{self.correlation_id}", tool_result)
                    self.agent.session.publish(Event("ToolResultEvent", tool_result, self.correlation_id))
                    central_logger.log_interaction(
                        self.agent.name, "System", f"Tool task completed: {tool_result}", self.agent.run_id
                    )
                    self.agent.interaction_stack.append(ToolResult(self.agent, tool_result))
                except Exception as e:
                    central_logger.log_interaction(
                        self.agent.name, "System", f"Tool task failed: {str(e)}", self.agent.run_id
                    )
                    self.agent.session.publish(Event("ToolFailureEvent", {"error": str(e)}, self.correlation_id))

    def transition_step(self):
        return None, {}

    def to_dict(self):
        return {"type": "WaitingForToolResult", "correlation_id": self.correlation_id, "task_id": self.task_id}

    @classmethod
    def from_dict(cls, data: dict, agent: "BaseAgent"):
        return cls(agent, data["correlation_id"], data.get("task_id"))

class ToolResult(State):
    def __init__(self, agent: "BaseAgent", result: str):
        super().__init__(agent)
        self.result = result

    def transition_step(self):
        return None, {}

    def to_dict(self):
        return {"type": "ToolResult", "result": self.result}

    @classmethod
    def from_dict(cls, data: dict, agent: "BaseAgent"):
        return cls(agent, data["result"])

class AgentCall(State):
    def __init__(self, agent: "BaseAgent", branches: List[Dict], correlation_id: str):
        super().__init__(agent)
        self.branches = branches
        self.correlation_id = correlation_id

    def on_enter(self):
        for branch in self.branches:
            sub_agent_name = branch.get("agent_name", f"SubAgent_{len(self.agent.session.agents)}")
            task = branch.get("task", "Default task")
            event = Event("SpawnAgentEvent", {
                "agent_name": sub_agent_name,
                "task": task,
                "parent_id": self.agent.id,
                "correlation_id": self.correlation_id
            })
            self.agent.session.publish(event)
        central_logger.log_interaction(
            self.agent.name, "System", f"Published SpawnAgentEvents for {len(self.branches)} branches", self.agent.run_id
        )
        self.agent.interaction_stack.append(WaitingForAgentResult(self.agent, self.correlation_id))

    def transition_step(self):
        return None, {}

    def to_dict(self):
        return {
            "type": "AgentCall",
            "branches": self.branches,
            "correlation_id": self.correlation_id
        }

    @classmethod
    def from_dict(cls, data: dict, agent: "BaseAgent"):
        return cls(agent, data["branches"], data["correlation_id"])

class WaitingForAgentResult(State):
    def __init__(self, agent: "BaseAgent", correlation_id: str):
        super().__init__(agent)
        self.correlation_id = correlation_id
        self.result = None

    def on_enter(self):
        self.agent.subscribe("AgentResultEvent", self.correlation_id)
        central_logger.log_interaction(
            self.agent.name, "System", f"Subscribed to AgentResultEvent with correlation_id: {self.correlation_id}", self.agent.run_id
        )

    def transition_step(self):
        return None, {}

    def to_dict(self):
        return {"type": "WaitingForAgentResult", "correlation_id": self.correlation_id}

    @classmethod
    def from_dict(cls, data: dict, agent: "BaseAgent"):
        return cls(agent, data["correlation_id"])

class AgentResult(State):
    def __init__(self, agent: "BaseAgent", result: str):
        super().__init__(agent)
        self.result = result

    def on_enter(self):
        central_logger.log_interaction(
            self.agent.name, "System", f"AgentResult received: {self.result}", self.agent.run_id
        )

    def transition_step(self) -> Tuple[str, Dict]:
        return "Finished", {"result": self.result}

    def to_dict(self) -> Dict:
        return {"type": "AgentResult", "result": self.result}

    @classmethod
    def from_dict(cls, data: Dict, agent: "BaseAgent"):
        return cls(agent, data["result"])