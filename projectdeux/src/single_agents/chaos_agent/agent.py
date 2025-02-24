from typing import Optional, List, Any
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from single_agents.base_agent import BaseAgent
from custom_logging.central_logger import central_logger

class ChaosAgent(BaseAgent):
    def __init__(
        self,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        name: str = "ChaosAgent",
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        tools: Optional[List[str]] = None
    ):
        super().__init__(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name=name,
            model=model,
            api_key=api_key,
            tools=tools
        )
        self.system_prompt = (
            "You are Chaos: unpredictable, creative, and cryptic. "
            "Respond in bizarre metaphors, whimsical riddles, and surreal imagery."
        )

    def interact(self, user_input: str) -> str:
        messages = self._format_messages(user_input)
        response = self.llm.query(
            messages=messages,
            metadata={"agent_name": self.name, "agent_id": self.id}
        )
        central_logger.log_interaction(self.name, "User", f"User input: {user_input}")
        central_logger.log_interaction(self.name, "System", f"Response: {response}")
        return response