# projectdeux/src/systems/scenario_manager.py

import os
import yaml

class ScenarioManager:
    def __init__(self, scenarios_dir: str):
        self.scenarios = {}
        if not os.path.isdir(scenarios_dir):
            raise ValueError(f"'{scenarios_dir}' is not a directory")

        for filename in os.listdir(scenarios_dir):
            if filename.endswith(".yaml") or filename.endswith(".yml"):
                filepath = os.path.join(scenarios_dir, filename)
                with open(filepath, "r") as f:
                    data = yaml.safe_load(f) or {}
                    for scenario in data.get("scenarios", []):
                        name = scenario.get("name", "Unnamed")
                        self.scenarios[name] = scenario

    def get_scenario(self, name: str):
        scenario = self.scenarios.get(name)
        if not scenario:
            raise ValueError(f"Scenario '{name}' not found.")
        return scenario

    def list_scenarios(self):
        return list(self.scenarios.keys())
