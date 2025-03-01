from src.systems.base_system import BaseSystem
from src.systems.collaborative_writing_system import CollaborativeWritingSystem
from src.tasks.celery_task_manager import CeleryTaskManager
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
import logging

logger = logging.getLogger(__name__)

# Registry for system classes
SYSTEM_REGISTRY = {
    "base_system": BaseSystem,  # Default system type
    "collaborative_writing_system": CollaborativeWritingSystem,
}

def load_system(config: dict):
    """Load a system based on the provided config."""
    system_type = config.get("system_type", "base_system")  # Default to base_system if not specified
    system_class = SYSTEM_REGISTRY.get(system_type)
    if not system_class:
        logger.error(f"Unknown system type '{system_type}'")
        raise ValueError(f"Unknown system type '{system_type}'")
    
    entity_manager = EntityManager()
    component_manager = ComponentManager()
    agent_configs = config.get("agents", [])
    
    # Initialize CeleryTaskManager with agent configurations
    task_manager = CeleryTaskManager(agent_configs=agent_configs)
    
    # Instantiate the system, letting it create agents from config
    system = system_class(
        config=config,
        entity_manager=entity_manager,
        component_manager=component_manager,
        task_manager=task_manager
    )
    return system