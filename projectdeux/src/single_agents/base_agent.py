from abc import abstractmethod
from typing import Optional, List, Any, Dict
from entities.smart_entity import SmartEntity
from integrations.llm.llm_client import LLMClient
from custom_logging.litellm_logger import my_custom_logging_fn

class BaseAgent(SmartEntity):
    def __init__(
        self,
        name: str,
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        system_prompt: str = "You are a helpful assistant"
    ):
        super().__init__(entity_type="agent", name=name)
        self.model = model
        self.api_key = api_key
        self.tools = tools or []
        self.system_prompt = system_prompt
        self.llm = LLMClient(
            model=self.model,
            api_key=self.api_key,
            logger_fn=my_custom_logging_fn
        )

    @abstractmethod
    def interact(self, user_input: str) -> str:
        """Process input and return agent's response"""
        pass

    def _format_messages(self, user_input: str) -> List[Dict]:
        """Create message structure for LLM"""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]