from typing import Optional, List, Any
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from single_agents.base_agent import BaseAgent
from custom_logging.central_logger import central_logger

class SimpleAgent(BaseAgent):
    def __init__(
        self,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        name: str = "SimpleAgent",
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        tools: Optional[List[str]] = None,
        system_prompt: str = "You are a helpful and concise assistant"
    ):
        super().__init__(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name=name,
            model=model,
            api_key=api_key,
            tools=tools,
            system_prompt=system_prompt
        )

    def interact(self, user_input: str) -> str:
        messages = self._format_messages(user_input)
        metadata = {
            "agent_name": self.name,
            "agent_id": self.id,
            "system_prompt": self.system_prompt
        }
        try:
            response = self.llm.query(messages=messages, metadata=metadata)
            central_logger.log_interaction(self.name, "User", f"User input: {user_input}")
            central_logger.log_interaction(self.name, "System", f"Response: {response}")
            return response
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            central_logger.log_interaction(self.name, "System", error_msg)
            return error_msg