# main.py
import argparse
from src.systems.scenario_manager import ScenarioManager
from src.systems.scenario_loader import load_system
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    parser = argparse.ArgumentParser(description="Run a multi-agent scenario.")
    parser.add_argument("--scenarios", required=True, help="Path to scenarios directory")
    parser.add_argument("--scenario", required=True, help="Name of the scenario to run")
    args = parser.parse_args()

    try:
        manager = ScenarioManager(args.scenarios)
        scenario = manager.get_scenario(args.scenario)
        system = load_system(scenario)
        result = system.run(**scenario.get("run_params", {}))
        print("System run complete. Final result:\n", result)
    except ValueError as e:
        logger.error(f"Error loading or running scenario: {e}")
        raise  # Re-raise to notify the user, or handle gracefully depending on your needs
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        raise

if __name__ == "__main__":
    main()