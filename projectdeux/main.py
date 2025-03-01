import argparse
import atexit
from src.systems.scenario_manager import ScenarioManager
from src.systems.scenario_loader import load_system
from src.custom_logging.central_logger import central_logger
from src.custom_logging.litellm_logger import flush_logs as flush_litellm_logs

def main():
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run a multi-agent scenario.")
    parser.add_argument("--scenarios", required=True, help="Path to scenarios directory")
    parser.add_argument("--scenario", required=True, help="Name of the scenario to run")
    args = parser.parse_args()

    # Register log flush handlers
    atexit.register(central_logger.flush_logs)
    atexit.register(flush_litellm_logs)

    # Load the scenario
    manager = ScenarioManager(args.scenarios)
    scenario = manager.get_scenario(args.scenario)

    # Initialize and run the system
    system = load_system(scenario)
    result = system.run(**scenario.get("run_params", {}))
    flush_litellm_logs()  # Manually flush LiteLLM logs after system run
    print("System run complete. Final result:\n", result)

if __name__ == "__main__":
    main()