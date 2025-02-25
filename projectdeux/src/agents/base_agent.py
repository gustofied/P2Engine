# agents/base_agent.py
from typing import Optional, List, Dict
from entities.entity import Entity
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from integrations.llm.llm_client import LLMClient
from custom_logging.litellm_logger import my_custom_logging_fn
from custom_logging.central_logger import central_logger

class BaseAgent(Entity):
    def __init__(
        self,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        name: str,
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        tools: Optional[List[str]] = None,
        system_prompt: str = "You are a helpful assistant",
        behaviors: Optional[Dict] = None
    ):
        super().__init__(entity_type="agent", name=name)
        self.model_name = model
        self.api_key = api_key
        self.system_prompt = system_prompt
        self.behaviors = behaviors or {}

        # Attach LLM client as Model component
        llm_client = LLMClient(model=self.model_name, api_key=self.api_key, logger_fn=my_custom_logging_fn)
        component_manager.attach_component(self, "model", client=llm_client)

        entity_manager.register(self)

        if tools:
            for tool in tools:
                component_manager.attach_component(self, "tool", tool_name=tool)

    @property
    def llm_client(self) -> LLMClient:
        """Access the LLM client via the model component."""
        model_component = self.get_component("model")
        if model_component and hasattr(model_component, 'client'):
            return model_component.client
        raise ValueError("Model component not found or invalid in BaseAgent")

    def _format_messages(self, user_input: str) -> List[Dict]:
        """Format messages using behavior or default system/user structure."""
        formatter = self.behaviors.get("format_messages", lambda x: [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": x}
        ])
        return formatter(user_input)

    def use_tool(self, user_input: str) -> Optional[str]:
        """Use a tool if available, based on behavior or default logic."""
        tool_fn = self.behaviors.get("use_tool", self._default_use_tool)
        tools = [t.tool_name for t in self.components.values() if t.name == "tool"]
        return tool_fn(user_input, tools)

    def _default_use_tool(self, user_input: str, tools: List[str]) -> Optional[str]:
        """Default tool usage logic (e.g., calculator)."""
        if "calculate" in user_input.lower() and "calculator" in tools:
            try:
                calc_input = user_input.lower().split("calculate")[-1].strip()
                calc_input = "".join(c for c in calc_input if c.isdigit() or c in "+-*/()")
                result = eval(calc_input)
                central_logger.log_interaction(self.name, "Tool", f"Used calculator: {calc_input} = {result}")
                return str(result)
            except Exception as e:
                error_msg = f"Error using calculator: {str(e)}"
                central_logger.log_interaction(self.name, "Tool", error_msg)
                return error_msg
        return None

    def interact(self, user_input: str) -> str:
        """Interact with the user, using tools or LLM as needed."""
        tool_response = self.use_tool(user_input)
        if tool_response:
            return tool_response

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