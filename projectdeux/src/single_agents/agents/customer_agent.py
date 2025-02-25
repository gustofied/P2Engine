# File: multi_agent_system/agents/customer_agent.py

from ..base_agent import BaseAgent
from custom_logging.central_logger import central_logger

class CustomerAgent(BaseAgent):
    def __init__(self, entity_manager, component_manager, name, model="gpt-3.5-turbo", api_key=None, tools=None):
        super().__init__(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name=name,
            model=model,
            api_key=api_key,
            tools=tools,
            system_prompt="You are a customer seeking assistance."
        )

    def interact(self, user_input: str) -> str:
        """Customer agent's interaction logic."""
        central_logger.log_interaction(self.name, "User", f"Input: {user_input}")
        messages = self._format_messages(user_input)
        response = self.llm.query(messages=messages, metadata={"agent_name": self.name, "agent_id": self.id})
        central_logger.log_interaction(self.name, "System", f"Response: {response}")
        return response