from .base_system import BaseSystem
from src.agents.factory import AgentFactory
from src.custom_logging.central_logger import central_logger
from typing import List, Dict

class GenericSystem(BaseSystem):
    """A generic system that builds workflows from predefined sequences or supervisor decisions."""
    
    def __init__(self, agents, entity_manager, component_manager, config, task_manager=None):
        execution_type = config.get("execution_type", "synchronous")
        super().__init__(
            agents=agents,
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=config,
            task_manager=task_manager,
            execution_type=execution_type
        )
        self.available_tasks = config.get("available_tasks", [])
        self.agents = {agent.name: agent for agent in agents}

    def define_workflow(self) -> List[Dict]:
        """Define the workflow based on config: either predefined or dynamic."""
        if "task_sequence" in self.config:
            workflow = self.config["task_sequence"]
        else:
            supervisor = next((agent for agent in self.agents.values() if agent.role == "supervisor"), None)
            if not supervisor:
                raise ValueError("No supervisor agent found for dynamic workflow")
            available_tasks_str = ", ".join(self.available_tasks)
            topic = self.config.get("run_params", {}).get("topic", "General")
            prompt = (
                f"You are planning a {self.system_type} project on the topic: {topic}. "
                f"Task: '{self.config['problem']}'. "
                "Define agents with 'name', 'role', 'system_prompt'. "
                f"Available tasks: {available_tasks_str}. "
                "Also, specify the 'task_sequence' as a list of {{'task_name': task, 'agent_name': name}}."
                "Return JSON with 'agents' (array) and 'task_sequence'."
            )
            decision = supervisor.decide_agents(prompt)
            agent_configs = decision["agents"]
            workflow = decision["task_sequence"]
            for config in agent_configs:
                if config["name"] not in self.agents:
                    new_agent = AgentFactory.create_agent(
                        self.entity_manager, self.component_manager, config
                    )
                    self.agents[config["name"]] = new_agent
                    central_logger.log_interaction("System", "Debug", f"Created agent: {config['name']}")
        return workflow

    def build_workflow_from_sequence(self, task_sequence: List[str], agent_configs: List[Dict]) -> List[Dict]:
        """Build a workflow from a sequence of roles, ensuring compatibility with execution type."""
        workflow = []
        topic = self.config.get("run_params", {}).get("topic", "General")
        scenario_data = {
            "goal": self.goal,
            "problem": self.config.get("problem", "No problem defined"),
            "system_prompts": {agent.name: agent.system_prompt for agent in self.get_all_agents()},
            "agent_names": {agent.id: agent.name for agent in self.get_all_agents()}
        }
        role_to_config = {config["role"]: config for config in agent_configs}
        for i, role in enumerate(task_sequence):
            config = role_to_config.get(role)
            if config:
                agent = self.get_agent_by_name(config["name"])
                if agent:
                    task_name = config["task"]
                    queue = config.get("queue", "default")
                    args = [agent.id, topic, scenario_data] if i == 0 else [agent.id]
                    task_config = {
                        "task_name": task_name,
                        "args": args,
                        "queue": queue,
                        "agent_name": config["name"]
                    }
                    workflow.append(task_config)
                else:
                    self.logger.warning(f"Agent '{config['name']}' not found for role '{role}'")
            else:
                self.logger.warning(f"No agent config found for role '{role}'")
        return workflow

    def register_tasks(self):
        """No task registration here; assume tasks are registered globally."""
        pass