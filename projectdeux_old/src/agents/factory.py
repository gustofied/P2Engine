from typing import Dict, Optional, TYPE_CHECKING
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.states.state_registry import StateRegistry

if TYPE_CHECKING:
    from src.systems.base_system import BaseSystem

from .base_agent import BaseAgent
from .supervisor_agent import SupervisorAgent
from src.integrations.tools.tool_registry import ToolRegistry

class AgentFactory:
    @staticmethod
    def create_agent(
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        api_key: Optional[str] = None,
        session: Optional["BaseSystem"] = None,
        state_registry: Optional[StateRegistry] = None,
        run_id: Optional[str] = None
    ) -> BaseAgent:
        """Creates an agent based on the provided configuration."""
        name = config.get("name", "UnnamedAgent")
        model = config.get("model", "openrouter/qwen/qwq-32b:free")
        system_prompt = config.get("system_prompt", "You are a helpful assistant")
        tools_config = config.get("tools", [])
        behaviors = config.get("behaviors", {})
        role = config.get("role", "unknown").lower()

        tool_instances = []
        missing_tools = []
        for tool_name in tools_config:
            # Optional: Add type checking for robustness
            if not isinstance(tool_name, str):
                raise ValueError(f"Tool name must be a string, got {type(tool_name)}: {tool_name}")
            tool_class = ToolRegistry.get(tool_name)
            if tool_class:
                tool_instances.append(tool_class())
            else:
                missing_tools.append(tool_name)
        if missing_tools:
            raise ValueError(f"Missing tools: {', '.join(missing_tools)}")

        api_key = api_key or config.get("api_key")
        state_registry = state_registry or (session.state_registry if session else StateRegistry("src/scenarios/test_scenario.yaml"))

        if role == "supervisor":
            system_type = config.get("system_type", "collaborative_writing")
            agent = SupervisorAgent(
                system_type=system_type,
                entity_manager=entity_manager,
                component_manager=component_manager,
                name=name,
                model=model,
                api_key=api_key,
                tools=tool_instances,
                system_prompt=system_prompt,
                behaviors=behaviors,
                session=session,
                state_registry=state_registry,
                run_id=run_id
            )
        else:
            agent = BaseAgent(
                entity_manager=entity_manager,
                component_manager=component_manager,
                name=name,
                state_registry=state_registry,
                model=model,
                api_key=api_key,
                tools=tool_instances,
                system_prompt=system_prompt,
                behaviors=behaviors,
                session=session,
                run_id=run_id
            )
        
        agent.role = role
        return agent