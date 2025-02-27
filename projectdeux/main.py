import argparse
from systems.scenario_manager import ScenarioManager
from systems.scenario_loader import load_system

def main():
    parser = argparse.ArgumentParser(description="Run a scenario.")
    parser.add_argument("--scenarios", type=str, required=True, help="Path to scenarios directory")
    parser.add_argument("--scenario", type=str, required=True, help="Name of the scenario to run")
    args = parser.parse_args()

    scenario_manager = ScenarioManager(args.scenarios)
    scenario_config = scenario_manager.get_scenario(args.scenario)
    system = load_system(scenario_config)
    result = system.run(**scenario_config.get("run_params", {}))
    print(result)

if __name__ == "__main__":
    main()