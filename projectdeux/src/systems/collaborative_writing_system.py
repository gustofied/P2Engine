from .base_system import BaseSystem
from celery import chain
from src.tasks.celery_tasks import TASK_REGISTRY  # Import the task registry
from src.agents.factory import AgentFactory
from src.custom_logging.central_logger import central_logger
from src.custom_logging.litellm_logger import GLOBAL_LOG_DATA
from src.agents.supervisor_agent import SupervisorAgent
from typing import Dict

class CollaborativeWritingSystem(BaseSystem):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.agents = {}
        for agent_config in self.config.get("agents", []):
            if agent_config.get("role") == "supervisor":
                agent = SupervisorAgent(
                    entity_manager=self.entity_manager,
                    component_manager=self.component_manager,
                    name=agent_config["name"],
                    model=agent_config.get("model", "deepseek/deepseek-chat"),
                    api_key=agent_config.get("api_key"),
                    system_prompt=agent_config["system_prompt"]
                )
                self.agents[agent.name] = agent

    def spawn_agent(self, agent_config: Dict):
        """Spawn a new agent dynamically and update the task manager."""
        agent = AgentFactory.create_agent(
            entity_manager=self.entity_manager,
            component_manager=self.component_manager,
            config=agent_config
        )
        self.agents[agent.name] = agent
        self.task_manager.agent_queues[agent.name] = agent_config["queue"]
        central_logger.log_interaction(
            sender="CollaborativeWritingSystem",
            receiver="System",
            message=f"Spawned new agent: {agent.name} with role {agent.role} and queue {agent_config['queue']}"
        )
        return agent

    def run(self, **kwargs):
        """Run the system using the problem from the config."""
        problem = self.config["problem"]
        self.log_start(problem)
        domain = kwargs.get("domain", "General")

        # Find the supervisor agent
        supervisor = next((agent for agent in self.agents.values() if isinstance(agent, SupervisorAgent)), None)
        if not supervisor:
            raise ValueError("No supervisor agent found in the system.")

        # Get agent configurations and task sequence from the supervisor
        decision = supervisor.decide_agents(problem)
        agent_configs = decision["agents"]
        task_sequence = decision["task_sequence"]

        # Spawn agents dynamically
        for config in agent_configs:
            self.spawn_agent(config)

        # Map agents to roles (excluding supervisor)
        role_to_agent = {agent.role: agent for agent in self.agents.values() if hasattr(agent, 'role') and agent.role != "supervisor"}

        # Prepare scenario data
        system_prompts = {agent.id: agent.system_prompt for agent in self.agents.values()}
        agent_names = {agent.id: agent.name for agent in self.agents.values()}
        scenario_data = {
            "goal": self.goal,
            "problem": problem,
            "system_prompts": system_prompts,
            "agent_names": agent_names
        }

        # Build the task chain dynamically using the TASK_REGISTRY
        tasks = []
        for role in task_sequence:
            agent_config = next((a for a in agent_configs if a["role"] == role), None)
            if agent_config and "task" in agent_config:
                task_name = agent_config["task"]
                task_func = TASK_REGISTRY.get(task_name)
                if task_func:
                    agent = role_to_agent.get(role)
                    if agent:
                        queue = self.task_manager.agent_queues.get(agent.name, "default")
                        if role == "researcher":
                            task = task_func["function"].s(agent.id, domain, scenario_data).set(queue=queue)
                            tasks.append(task)
                            print(f"Added task {task_name} for role {role} to queue {queue}")
                        else:
                            task = task_func["function"].s(agent.id).set(queue=queue)
                            tasks.append(task)
                            print(f"Added task {task_name} for role {role} to queue {queue}")
                else:
                    central_logger.log_interaction(
                        sender="CollaborativeWritingSystem",
                        receiver="System",
                        message=f"Task '{task_name}' not found in registry for role '{role}'. Skipping."
                    )
            else:
                central_logger.log_interaction(
                    sender="CollaborativeWritingSystem",
                    receiver="System",
                    message=f"No agent or task defined for role '{role}'. Skipping."
                )

        if not tasks:
            raise ValueError("No valid tasks to execute based on supervisor's sequence.")

        # Execute the task chain
        full_chain = chain(*tasks)
        async_result = full_chain()
        final_article, all_logs, scenario_data, all_litellm_logs = async_result.get(timeout=500)

        # Log the results
        for log in all_logs:
            central_logger.log_interaction(sender=log["from"], receiver=log["to"], message=log["message"])
        for log in all_litellm_logs:
            agent_id = log["agent_id"]
            if agent_id not in GLOBAL_LOG_DATA["agents"]:
                GLOBAL_LOG_DATA["agents"][agent_id] = {"calls": []}
            GLOBAL_LOG_DATA["agents"][agent_id]["calls"].append(log)

        # Prepare all agents for logging
        all_agents = {
            agent.id: {
                "type": agent.__class__.__name__,
                "name": agent.name,
                "role": getattr(agent, "role", "unknown"),
                "components": {k: str(v) for k, v in agent.components.items()}
            } for agent in self.agents.values()
        }

        final_result_md = f"# Final Article\n\n{final_article}"
        central_logger.log_system_end(final_result_md, {"success": True}, 10, all_agents)
        return final_result_md