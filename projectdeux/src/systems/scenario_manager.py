import os
import yaml

class ScenarioManager:
    def __init__(self, scenarios_dir):
        self.scenarios = {}
        if not os.path.isdir(scenarios_dir):
            raise ValueError(f"'{scenarios_dir}' is not a directory")
        
        for filename in os.listdir(scenarios_dir):
            if filename.endswith('.yaml') or filename.endswith('.yml'):
                file_path = os.path.join(scenarios_dir, filename)
                with open(file_path, 'r') as file:
                    config = yaml.safe_load(file)
                    # Assuming each file contains a list under 'scenarios'
                    for scenario in config.get('scenarios', []):
                        self.scenarios[scenario['name']] = scenario

    def get_scenario(self, scenario_name):
        scenario = self.scenarios.get(scenario_name)
        if not scenario:
            raise ValueError(f"Scenario '{scenario_name}' not found")
        return scenario

    def list_scenarios(self):
        return list(self.scenarios.keys())