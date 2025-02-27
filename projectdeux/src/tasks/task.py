from typing import Optional, List, Dict
from agents.base_agent import BaseAgent
from custom_logging.central_logger import central_logger

class Task:
    def __init__(self, agent, instruction, context=None, dependencies=None, **kwargs):
        self.agent = agent
        self.instruction = instruction
        self.context = context
        self.dependencies = dependencies or []
        self.stream = kwargs.get("stream", False)
        self.initial_response = kwargs.get("initial_response", False)

    def execute(self):
        """Execute the task, returning a generator if streaming, or a string if not."""
        if self.stream:
            return self._execute_streaming()
        else:
            return self._execute_non_streaming()

    def _execute_streaming(self):
        """Generator method for streaming responses."""
        if self.initial_response:
            yield self.agent.interact("Provide a quick initial response to: " + self.instruction)
        user_input = f"{self.context}\n{self.instruction}" if self.context else self.instruction
        response = self.agent.interact(user_input)
        for chunk in response.split():
            yield chunk

    def _execute_non_streaming(self):
        """Regular method for non-streaming execution."""
        if self.initial_response:
            initial_response = self.agent.interact("Provide a quick initial response to: " + self.instruction)
            print(initial_response)
        user_input = f"{self.context}\n{self.instruction}" if self.context else self.instruction
        response = self.agent.interact(user_input)
        central_logger.log_interaction(self.agent.name, "Task", f"Instruction: {self.instruction}, Response: {response}")
        return response

    @classmethod
    def create(cls, agent, instruction, context=None, dependencies=None, **kwargs):
        """Create and execute a task."""
        task = cls(agent, instruction, context, dependencies, **kwargs)
        return task.execute()