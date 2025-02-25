# systems/scenario_loader.py
import json
import importlib
from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from agents.factory import AgentFactory  # Updated import

def to_camel_case(snake_str: str) -> str:
    """Convert snake_case to CamelCase."""
    parts = snake_str.split('_')
    return ''.join(part.capitalize() for part in parts)

def load_system(system_name: str, config_path: str):
    print(f"Loading system: {system_name} from config: {config_path}")
    try:
        system_module = importlib.import_module(f"systems.{system_name}.{system_name}")
        class_name = f"{to_camel_case(system_name)}System"
        system_class = getattr(system_module, class_name)
        print(f"Loaded system class: {system_class.__name__}")
    except ImportError as e:
        print(f"Error importing module 'systems.{system_name}.{system_name}': {e}")
        raise
    except AttributeError as e:
        print(f"Error: Class '{class_name}' not found in module: {e}")
        raise

    try:
        with open(config_path, "r") as f:
            config = json.load(f)
        print(f"Loaded config: {config}")
    except FileNotFoundError as e:
        print(f"Error: Config file '{config_path}' not found: {e}")
        raise
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{config_path}': {e}")
        raise

    entity_manager = EntityManager()
    component_manager = ComponentManager()
    print("Initialized entity and component managers")

    agents = []
    for agent_config in config.get("agents", []):
        try:
            agent = AgentFactory.create_agent(
                entity_manager=entity_manager,
                component_manager=component_manager,
                config=agent_config
            )
            agents.append(agent)
            print(f"Loaded agent: {agent_config['name']}")
        except Exception as e:
            print(f"Error creating agent from config {agent_config}: {e}")
            raise

    try:
        system = system_class(agents, entity_manager, component_manager, config)
        print(f"System '{system_name}' initialized successfully")
        return system
    except Exception as e:
        print(f"Error initializing system '{class_name}': {e}")
        raise

if __name__ == "__main__":
    try:
        system = load_system("adaptive_scenario", "src/systems/adaptive_scenario/scenarios/scenario1.json")
        print(f"Test load successful: {system}")
    except Exception as e:
        print(f"Test failed: {e}")