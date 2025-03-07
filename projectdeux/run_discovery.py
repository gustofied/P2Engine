import argparse
import yaml
from src.systems.meta_system_inventor import MetaSystemInventor  # Updated import
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.agents.factory import AgentFactory
import uuid

def run_discovery(scenario_path, iterations=15):
    with open(scenario_path, 'r') as f:
        scenario = yaml.safe_load(f)['scenarios'][0]

    entity_manager = EntityManager()
    component_manager = ComponentManager()
    agents = [
        AgentFactory.create_agent(entity_manager, component_manager, agent_config)
        for agent_config in scenario['agents']
    ]

    scenario['iterations'] = iterations

    system = MetaSystemInventor(  # Changed from DiscoverySystem
        agents=agents,
        entity_manager=entity_manager,
        component_manager=component_manager,
        config=scenario,
        run_id=str(uuid.uuid4())
    )
    result = system.run()

    print(f"Best Architecture Explanation: {result['best_architecture']['explanation']}")
    print(f"Best Architecture Code:\n{result['best_architecture']['code']}")
    print(f"History Size: {len(result['history'])} iterations recorded.")
    print(f"Compendium generated in 'discovery/architectures_<run_id>.md'.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run the multi-agent discovery system.")
    parser.add_argument("--scenario", required=True, help="Path to scenario YAML file")
    parser.add_argument("--iterations", type=int, default=15, help="Number of iterations")
    args = parser.parse_args()
    run_discovery(args.scenario, args.iterations)
    