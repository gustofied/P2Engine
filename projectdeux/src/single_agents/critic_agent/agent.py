from typing import Optional, List, Any
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from single_agents.base_agent import BaseAgent
from custom_logging.central_logger import central_logger

class CriticAgent(BaseAgent):
    def __init__(
        self,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        name: str = "CriticAgent",
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
        self.critique_prompt = (
            "You are a critic analyzing the conversation. "
            "Based on the conversation so far, indicate if additional specialized agents are needed. "
            "If so, suggest the type or name of the new agent(s). If the problem is solved, simply say 'solved'."
        )

    def interact(self, conversation_history: str) -> str:
        prompt = f"{self.critique_prompt}\n\nConversation so far:\n{conversation_history}"
        messages = self._format_messages(prompt)
        response = self.llm.query(
            messages=messages,
            metadata={"agent_name": self.name, "agent_id": self.id}
        )
        central_logger.log_interaction(self.name, "System", f"Critique: {response}")
        return response