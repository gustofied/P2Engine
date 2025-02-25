from .scenario_loader import ScenarioLoader
from custom_logging.central_logger import central_logger

class ConfigurableSystem:
    def __init__(self, config_path):
        loader = ScenarioLoader(config_path)
        self.system, self.goal, self.problem, self.run_params = loader.load_scenario()
        self.scenario_name = loader.config["scenario"]
        central_logger.log_system_start(self.scenario_name, self.system.entity_manager.entities, self.problem, self.goal)

    def run(self):
        print(f"Running scenario: {self.scenario_name}")
        print(f"Goal: {self.goal}")
        result = self.system.run(**self.run_params)
        central_logger.log_system_end(result, {"success": len(result) > 0}, 10 if len(result) > 0 else -5)
        central_logger.flush_logs()
        print("\n=== FINAL RESULT ===")
        print(result)
        return result