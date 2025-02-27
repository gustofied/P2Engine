from typing import Dict, Optional
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from .base_agent import BaseAgent
from integrations.tools.tool_registry import ToolRegistry  # Assuming this exists

class AgentFactory:
    @staticmethod
    def create_agent(
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        api_key: Optional[str] = None
    ) -> BaseAgent:
        name = config.get("name", "UnnamedAgent")
        model = config.get("model", "github/gpt-4o")
        system_prompt = config.get("system_prompt", "You are a helpful assistant")
        tools_config = config.get("tools", [])
        behaviors = config.get("behaviors", {})

        # Map tool names to tool instances using ToolRegistry
        tool_instances = []
        missing_tools = []
        for tool_name in tools_config:
            tool_class = ToolRegistry.get(tool_name)
            if tool_class:
                tool_instances.append(tool_class())  # Instantiate the tool
            else:
                missing_tools.append(tool_name)
        if missing_tools:
            raise ValueError(f"Missing tools: {', '.join(missing_tools)}")

        api_key = api_key or config.get("api_key")

        return BaseAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name=name,
            model=model,
            api_key=api_key,
            tools=tool_instances,
            system_prompt=system_prompt,
            behaviors=behaviors
        )