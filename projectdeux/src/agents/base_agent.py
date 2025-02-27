from typing import Optional, List, Dict
from entities.entity import Entity
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from integrations.llm.llm_client import LLMClient
from custom_logging.litellm_logger import my_custom_logging_fn
from custom_logging.central_logger import central_logger
from integrations.tools.base_tool import Tool

class BaseAgent(Entity):
    def __init__(
        self,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        name: str,
        model: str = "github/gpt-4o",
        api_key: Optional[str] = None,
        tools: Optional[List[Tool]] = None,
        system_prompt: str = "You are a helpful assistant",
        behaviors: Optional[Dict] = None
    ):
        super().__init__(entity_type="agent", name=name)
        self.model_name = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.behaviors = behaviors or {}
        self.tools = tools or []

        # Attach LLM client as Model component
        llm_client = LLMClient(model=self.model_name, api_key=self.api_key, logger_fn=my_custom_logging_fn)
        component_manager.attach_component(self, "model", client=llm_client)

        entity_manager.register(self)

    @property
    def llm_client(self) -> LLMClient:
        """Access the LLM client via the model component."""
        model_component = self.get_component("model")
        if model_component and hasattr(model_component, 'client'):
            return model_component.client
        raise ValueError("Model component not found or invalid in BaseAgent")

    def interact(self, user_input: str) -> str:
        """Interact with the user, using tools if applicable or LLM otherwise."""
        for tool in self.tools:
            if tool.__class__.__name__ == "WebScraperTool" and user_input.lower().startswith("scrape"):
                parts = user_input.split(" ", 2)
                if len(parts) == 3:
                    url, target = parts[1], parts[2]
                    return tool.execute(url=url, target=target)
                else:
                    return tool.execute(url=parts[1])
        
        # If no tool matches, use the LLM
        messages = self._format_messages(user_input)
        metadata = {"agent_name": self.name, "agent_id": self.id, "system_prompt": self.system_prompt}
        try:
            response = self.llm_client.query(messages=messages, metadata=metadata)
            central_logger.log_interaction(self.name, "User", f"User input: {user_input}")
            central_logger.log_interaction(self.name, "System", f"Response: {response}")
            return response
        except Exception as e:
            error_msg = f"Error generating response: {str(e)}"
            central_logger.log_interaction(self.name, "System", error_msg)
            return error_msg

    def _format_messages(self, user_input: str) -> List[Dict]:
        """Format messages using behavior or default system/user structure."""
        formatter = self.behaviors.get("format_messages", lambda x: [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": x}
        ])
        return formatter(user_input)