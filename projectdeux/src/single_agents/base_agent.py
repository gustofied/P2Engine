from abc import abstractmethod
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
        system_prompt: str = "You are a helpful assistant"
    ):
        super().__init__(entity_type="agent", name=name)
        self.model = model
        self.api_key = api_key
        self.system_prompt = system_prompt

        # Create LLM client and attach it as an LLM component.
        self.llm = LLMClient(
            model=self.model,
            api_key=self.api_key,
            logger_fn=my_custom_logging_fn
        )
        component_manager.attach_component(self, "llm", client=self.llm)

        # Register the agent.
        entity_manager.register(self)

        # Attach any tool components if provided.
        if tools:
            for tool in tools:
                component_manager.attach_component(self, "tool", tool_name=tool)

    @abstractmethod
    def interact(self, user_input: str) -> str:
        """Process input and return agent's response."""
        pass

    def _format_messages(self, user_input: str) -> List[Dict]:
        """Create message structure for LLM."""
        return [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]

    def has_tool(self, tool_name: str) -> bool:
        """Check if the agent has a specific tool."""
        tool = self.get_component("tool")
        return tool is not None and tool.tool_name == tool_name

    def get_connections(self) -> List[str]:
        """Get list of connected entity IDs."""
        connections = []
        for component in self.components.values():
            if component.name == "connection":
                connections.append(component.target_entity_id)
        return connections

    def use_tool(self, user_input: str) -> Optional[str]:
        """Use a tool if available and applicable."""
        tool = self.get_component("tool")
        if not tool:
            return None
        if tool.tool_name == "calculator" and "calculate" in user_input.lower():
            try:
                # Extract and clean calculation input.
                calc_input = user_input.lower().split("calculate")[-1].strip()
                # Remove any non-math characters (simplified).
                calc_input = "".join(c for c in calc_input if c.isdigit() or c in "+-*/()")
                result = eval(calc_input)
                central_logger.log_interaction(
                    self.name,
                    "Tool",
                    f"Used {tool.tool_name}: {calc_input} = {result}"
                )
                return str(result)
            except Exception as e:
                error_msg = f"Error using {tool.tool_name}: {str(e)}"
                central_logger.log_interaction(self.name, "Tool", error_msg)
                return error_msg
        return None
