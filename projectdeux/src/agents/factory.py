# agents/factory.py
from typing import Dict, Optional
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from .base_agent import BaseAgent

class AgentFactory:
    @staticmethod
    def create_agent(
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        api_key: Optional[str] = None
    ) -> BaseAgent:
        """
        Create a BaseAgent instance based on a configuration dictionary.

        Args:
            entity_manager (EntityManager): The entity manager instance.
            component_manager (ComponentManager): The component manager instance.
            config (Dict): Configuration dictionary with agent settings.
            api_key (Optional[str]): Optional API key for the LLM client.

        Returns:
            BaseAgent: An instance of BaseAgent configured with the provided settings.
        """
        name = config.get("name", "UnnamedAgent")
        model = config.get("model", "github/gpt-4o")
        system_prompt = config.get("system_prompt", "You are a helpful assistant")
        tools = config.get("tools", [])
        behaviors = config.get("behaviors", {})

        # Use the provided api_key or fallback to the config
        api_key = api_key or config.get("api_key")

        return BaseAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name=name,
            model=model,
            api_key=api_key,
            tools=tools,
            system_prompt=system_prompt,
            behaviors=behaviors
        )