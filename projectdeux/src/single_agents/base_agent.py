from abc import abstractmethod
from typing import Optional, List, Any
from entities.smart_entity import SmartEntity
from integrations.llm.llm_client import LLMClient
from custom_logging.litellm_logger import my_custom_logging_fn

class BaseAgent(SmartEntity):
    def __init__(
        self,
        name: str,
        model: str = "gpt-3.5-turbo",  # Each agent can choose a model
        api_key: Optional[str] = None,
        tools: Optional[List[Any]] = None
    ):
        super().__init__(entity_type="agent", name=name)
        self.model = model
        self.api_key = api_key
        self.tools = tools or []
        self.llm = LLMClient(
            model=self.model,           # Pass the chosen model to LLMClient
            api_key=self.api_key,
            logger_fn=my_custom_logging_fn
        )

    @abstractmethod
    def interact(self, user_input: str) -> str:
        """
        Agents must implement how they interact with a prompt.
        """
        pass
