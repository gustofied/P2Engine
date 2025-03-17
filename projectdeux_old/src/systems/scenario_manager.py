import os
from typing import Optional
import yaml
from src.systems.generic_system import GenericSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.agents.factory import AgentFactory
from src.custom_logging.central_logger import central_logger

SYSTEM_REGISTRY = {
    "generic": GenericSystem,
}

class ScenarioManager:
    def __init__(self, scenarios_dir: str):
        self.scenarios_dir = scenarios_dir
        self.scenarios = {}
        if not os.path.isdir(scenarios_dir):
            raise ValueError(f"'{scenarios_dir}' is not a directory")
        for filename in os.listdir(scenarios_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(scenarios_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        scenario = yaml.safe_load(f)
                        if scenario:
                            name = scenario.get("name", os.path.splitext(filename)[0])
                            self.scenarios[name] = scenario
                            central_logger.log_interaction("ScenarioManager", "System", f"Loaded scenario '{name}' from {filepath}", "init")
                except Exception as e:
                    central_logger.log_error("ScenarioManager", e, "init", context={"action": "load_scenario", "filepath": filepath})

    def get_scenario(self, name: str):
        scenario = self.scenarios.get(name)
        if not scenario:
            raise ValueError(f"Scenario '{name}' not found.")
        return scenario

    def list_scenarios(self):
        return list(self.scenarios.keys())

    def load_system(self, scenario_name: str, run_id: Optional[str] = None):
        """Load a system instance based on the scenario configuration."""
        try:
            scenario = self.get_scenario(scenario_name)
            system_type = scenario.get("system_type")
            system_class = SYSTEM_REGISTRY.get(system_type)
            if not system_class:
                raise ValueError(f"Unknown system type '{system_type}'")
            
            entity_manager = EntityManager()
            component_manager = ComponentManager()
            agent_configs = scenario.get("agents", [])
            
            agents = [
                AgentFactory.create_agent(
                    entity_manager=entity_manager,
                    component_manager=component_manager,
                    config=agent_config
                ) for agent_config in agent_configs
            ]

            config_path = os.path.join(self.scenarios_dir, f"{scenario_name}.yaml")
            
            system = system_class(
                agents=agents,
                config_path=config_path,
                entity_manager=entity_manager,
                component_manager=component_manager,
                config=scenario,
                run_id=run_id
            )
            central_logger.log_interaction("ScenarioManager", "System", f"Loaded system for scenario '{scenario_name}' with run_id '{run_id}'", run_id)
            return system
        except Exception as e:
            central_logger.log_error("ScenarioManager", e, run_id, context={"action": "load_system", "scenario_name": scenario_name})
            raise