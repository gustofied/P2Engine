from src.systems.generic_system import GenericSystem
from projectdeux.discovery.meta_system_inventor import MetaSystemInventor  # Updated import
from src.tasks.task_manager import TaskManager
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.agents.factory import AgentFactory

SYSTEM_REGISTRY = {
    "generic": GenericSystem,
    "discovery": MetaSystemInventor,  # Changed from DiscoverySystem
}

def load_system(config: dict, run_id=None):
    system_type = config["system_type"]
    system_class = SYSTEM_REGISTRY.get(system_type)
    if not system_class:
        raise ValueError(f"Unknown system type '{system_type}'")
    
    entity_manager = EntityManager()
    component_manager = ComponentManager()
    agent_configs = config.get("agents", [])
    task_manager = TaskManager()
    
    agents = [
        AgentFactory.create_agent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=agent_config
        ) for agent_config in agent_configs
    ]

    system = system_class(
        agents=agents,
        entity_manager=entity_manager,
        component_manager=component_manager,
        config=config,
        task_manager=task_manager,
        run_id=run_id
    )
    return system