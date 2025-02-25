import json
import importlib
import re
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from single_agents.agents import agent_types

def camel_to_snake(name: str) -> str:
    s1 = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
    return re.sub('([a-z0-9])([A-Z])', r'\1_\2', s1).lower()

class ScenarioLoader:
    def __init__(self, config_path):
        with open(config_path, 'r') as f:
            self.config = json.load(f)
        self.entity_manager = EntityManager()
        self.component_manager = ComponentManager()
        self._validate_config()

    def _validate_config(self):
        required_fields = ["scenario", "system_type", "agents"]
        for field in required_fields:
            if field not in self.config:
                raise ValueError(f"Missing required field: {field}")
        for agent_config in self.config["agents"]:
            if agent_config["type"] not in agent_types:
                raise ValueError(f"Unknown agent type: {agent_config['type']}")

    def load_scenario(self):
        scenario_name = self.config["scenario"]
        system_type = self.config["system_type"]
        goal = self.config.get("goal", "No goal specified")
        run_params = self.config.get("run_params", {})
        problem = self.config.get("problem", "No problem specified")

        # Create agents
        agents = []
        for agent_config in self.config["agents"]:
            agent_type = agent_config["type"]
            agent_name = agent_config["name"]
            tools = agent_config.get("tools", [])
            model = agent_config.get("model", "gpt-3.5-turbo")
            api_key = agent_config.get("api_key")
            agent_class = agent_types[agent_type]
            agent = agent_class(
                entity_manager=self.entity_manager,
                component_manager=self.component_manager,
                name=agent_name,
                model=model,
                api_key=api_key,
                tools=tools
            )
            agents.append(agent)

        # Convert system_type from CamelCase to snake_case
        module_name = camel_to_snake(system_type)
        system_module = importlib.import_module(f"systems.{module_name}")
        system_class = getattr(system_module, system_type)
        system = system_class(agents, self.entity_manager, self.component_manager)

        return system, goal, problem, run_params
