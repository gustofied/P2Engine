from entities.entity_manager import EntityManager
from entities.component_manager import ComponentManager
from agents.factory import AgentFactory
from systems.web_scraping_system import WebScrapingSystem
from systems.research_system import ResearchSystem
from tasks.task_manager import TaskManager
from typing import Dict

SYSTEM_REGISTRY = {
    "web_scraping": WebScrapingSystem,
    "research_system": ResearchSystem
}

def load_system(config: Dict):
    """
    Load a system based on the provided configuration.

    Args:
        config (Dict): Configuration dictionary specifying system type, agents, tasks, etc.

    Returns:
        System instance configured with agents, tasks, and managers.

    Raises:
        ValueError: If system type or agent is invalid.
    """
    system_type = config["system_type"]
    system_class = SYSTEM_REGISTRY.get(system_type)
    if not system_class:
        raise ValueError(f"Unknown system type: {system_type}")

    entity_manager = EntityManager()
    component_manager = ComponentManager()
    agents = [AgentFactory.create_agent(entity_manager, component_manager, agent_conf)
              for agent_conf in config["agents"]]
    
    task_manager = TaskManager()
    agents_dict = {agent.name: agent for agent in agents}
    for task_config in config.get("tasks", []):
        agent = agents_dict.get(task_config["agent_name"])
        if not agent:
            raise ValueError(f"Agent '{task_config['agent_name']}' not found")
        task_manager.register_task(
            task_name=task_config["task_name"],
            agents=[agent],  # Pass agent as a single-item list
            instruction=task_config["instruction"],
            dependencies=task_config.get("dependencies", []),
            required_params=task_config.get("required_params", []),
            dependency_params=task_config.get("dependency_params", {})
        )

    system = system_class(
        agents=agents,
        entity_manager=entity_manager,
        component_manager=component_manager,
        config=config,
        task_manager=task_manager
    )
    system.goal = config.get("goal", "Solve a problem effectively")
    system.expected_result = config.get("expected_result", None)
    return system