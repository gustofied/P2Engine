# projectdeux/src/systems/scenario_manager.py
import os
import yaml
import logging

logger = logging.getLogger(__name__)

class ScenarioManager:
    def __init__(self, scenarios_dir: str):
        self.scenarios = {}
        if not os.path.isdir(scenarios_dir):
            raise ValueError(f"'{scenarios_dir}' is not a directory")

        for filename in os.listdir(scenarios_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(scenarios_dir, filename)
                try:
                    with open(filepath, "r") as f:
                        data = yaml.safe_load(f) or {}
                        for scenario in data.get("scenarios", []):
                            name = scenario.get("name", "Unnamed")
                            if name in self.scenarios:
                                logger.warning(f"Duplicate scenario name '{name}' in {filename}")
                            self.scenarios[name] = scenario
                            self._validate_scenario(scenario)
                except yaml.YAMLError as e:
                    logger.error(f"Error parsing YAML in {filename}: {e}")
                except Exception as e:
                    logger.error(f"Unexpected error loading {filename}: {e}")

    def _validate_scenario(self, scenario: dict):
        """Validate that the scenario has all required fields."""
        required_fields = ["name", "system_type", "problem", "goal", "agents"]
        for field in required_fields:
            if field not in scenario:
                raise ValueError(f"Scenario '{scenario.get('name', 'Unnamed')}' missing required field: {field}")

    def get_scenario(self, name: str):
        scenario = self.scenarios.get(name)
        if not scenario:
            raise ValueError(f"Scenario '{name}' not found.")
        return scenario

    def list_scenarios(self):
        return list(self.scenarios.keys())