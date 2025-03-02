# src/systems/collaborative_writing_system.py

from .base_system import BaseSystem
from src.tasks.task_registry import (
    register_task,
    plan_research,
    create_outline,
    writer_task,
    editor_task,
    finalize_article,
    TASK_REGISTRY
)
from src.agents.factory import AgentFactory
from src.custom_logging.central_logger import central_logger
from src.agents.supervisor_agent import SupervisorAgent
from typing import Dict, List

class CollaborativeWritingSystem(BaseSystem):
    def __init__(self, agents, entity_manager, component_manager, config, task_manager=None):
        super().__init__(
            agents=agents,
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=config,
            task_manager=task_manager,
            execution_type="asynchronous"
        )
        # Use the passed agents directly instead of reinitializing
        self.agents = {agent.name: agent for agent in agents}

    def get_agent_by_name(self, agent_name):
        """Retrieve an agent from the dictionary."""
        return self.agents.get(agent_name)

    def get_all_agents(self):
        """Return a list of all agent objects from the dictionary."""
        return list(self.agents.values())

    def define_workflow(self) -> List[Dict]:
        """Define the workflow based on execution_type."""
        if self.execution_type == "asynchronous":
            workflow = []
            # Use "topic" from run_params (defaulting to "General" if not provided)
            topic = self.config.get("run_params", {}).get("topic", "General")
            central_logger.log_interaction("System", "Debug", f"Config: {self.config}")
            
            if "task_sequence" in self.config:
                task_sequence = self.config["task_sequence"]
                central_logger.log_interaction("System", "Debug", f"Task sequence: {task_sequence}")
                agent_configs = self.config["agents"]
                role_to_agent = {agent["role"]: agent for agent in agent_configs}
                central_logger.log_interaction("System", "Debug", f"Role to agent mapping: {role_to_agent}")
                
                # Construct scenario_data with all predefined agents
                scenario_data = {
                    "goal": self.goal,
                    "problem": self.config["problem"],
                    "system_prompts": {agent.name: agent.system_prompt for agent in self.agents.values()},
                    "agent_names": {agent.id: agent.name for agent in self.agents.values()}
                }
                
                for i, role in enumerate(task_sequence):
                    agent_config = role_to_agent.get(role)
                    central_logger.log_interaction("System", "Debug", f"Role '{role}' -> Agent config: {agent_config}")
                    if agent_config:
                        task_name = agent_config["task"]
                        agent = self.get_agent_by_name(agent_config["name"])
                        central_logger.log_interaction("System", "Debug", f"Agent for '{agent_config['name']}': {agent}")
                        if agent:
                            queue = agent_config.get("queue", "default")
                            # For the first task, pass agent.id, topic, and scenario_data
                            if i == 0:
                                args = [agent.id, topic, scenario_data]
                            else:
                                args = [agent.id]
                            workflow.append({
                                "task_name": task_name,
                                "args": args,
                                "queue": queue
                            })
                            central_logger.log_interaction("System", "Debug", f"Added task: {task_name} for agent {agent.name}")
                        else:
                            central_logger.warning(f"No agent found for name '{agent_config['name']}'")
                    else:
                        central_logger.warning(f"No agent config found for role '{role}'")
            else:
                # If no task_sequence provided, use the supervisor's decision.
                supervisor = next((agent for agent in self.agents.values() if isinstance(agent, SupervisorAgent)), None)
                if not supervisor:
                    raise ValueError("No supervisor agent found.")
                
                available_tasks = ", ".join(TASK_REGISTRY.keys())
                prompt = (
                    f"You are an AI assistant planning a collaborative writing project on the topic: {self.config.get('run_params', {}).get('topic', 'General')}. "
                    f"The task is: '{self.config['problem']}'. "
                    "Determine which specialized AI agents are needed. "
                    "Each agent should have a 'name', 'role', 'task', 'queue', and 'system_prompt'. "
                    f"The 'task' must be one of the following: {available_tasks}. "
                    "Also, specify the 'task_sequence' (list of role names) for execution order. "
                    "Return a JSON object with 'agents' (array of agent configs) and 'task_sequence'."
                    "\n\nExample response:\n```json\n"
                    "{\n  \"agents\": [\n    {\"name\": \"ResearchBot\", \"role\": \"researcher\", \"task\": \"plan_research\", \"queue\": \"research_queue\", \"system_prompt\": \"Research thoroughly.\"},\n"
                    "    {\"name\": \"OutlineBot\", \"role\": \"outliner\", \"task\": \"create_outline\", \"queue\": \"outlining_queue\", \"system_prompt\": \"Create an outline.\"}\n  ],\n"
                    "  \"task_sequence\": [\"researcher\", \"outliner\"]\n}\n```"
                )
                decision = supervisor.decide_agents(prompt)
                valid_agents = []
                skipped_tasks = []
                for agent_config in decision["agents"]:
                    task_name = agent_config["task"]
                    if task_name in TASK_REGISTRY:
                        valid_agents.append(agent_config)
                    else:
                        skipped_tasks.append(task_name)
                        central_logger.warning(f"Task '{task_name}' not in TASK_REGISTRY; agent '{agent_config['name']}' skipped.")
                
                if skipped_tasks and not valid_agents:
                    central_logger.error("All suggested tasks were invalid; cannot proceed.")
                    raise ValueError(f"No valid tasks to execute. Skipped: {', '.join(skipped_tasks)}")
                
                # Create and store new agents if needed
                for agent_config in valid_agents:
                    agent_name = agent_config["name"]
                    if agent_name not in self.agents:
                        new_agent = AgentFactory.create_agent(
                            entity_manager=self.entity_manager,
                            component_manager=self.component_manager,
                            config=agent_config
                        )
                        self.agents[agent_name] = new_agent
                        central_logger.log_interaction("System", "Debug", f"Created agent: {agent_name}")
                
                # Construct scenario_data with all agents (initial + dynamically created)
                scenario_data = {
                    "goal": self.goal,
                    "problem": self.config["problem"],
                    "system_prompts": {agent.name: agent.system_prompt for agent in self.agents.values()},
                    "agent_names": {agent.id: agent.name for agent in self.agents.values()}
                }
                
                task_sequence = decision["task_sequence"]
                role_to_agent = {agent["role"]: agent for agent in valid_agents}
                for i, role in enumerate(task_sequence):
                    agent_config = role_to_agent.get(role)
                    if agent_config:
                        task_name = agent_config["task"]
                        agent = self.get_agent_by_name(agent_config["name"])
                        if agent is None:
                            central_logger.error(f"Agent '{agent_config['name']}' not found after creation.")
                            raise ValueError(f"Agent '{agent_config['name']}' not found in self.agents")
                        queue = agent_config.get("queue", "default")
                        if i == 0:
                            args = [agent.id, topic, scenario_data]
                        else:
                            args = [agent.id]
                        workflow.append({
                            "task_name": task_name,
                            "args": args,
                            "queue": queue
                        })
            central_logger.log_interaction("System", "Debug", f"Final workflow: {workflow}")
            return workflow
        else:
            workflow = []
            if "task_sequence" in self.config:
                task_sequence = self.config["task_sequence"]
                agent_configs = self.config["agents"]
                role_to_agent = {agent["role"]: agent for agent in agent_configs}
                for role in task_sequence:
                    workflow.append({
                        "task_name": agent_configs.get(role)["task"],
                        "agent_name": agent_configs.get(role)["name"],
                        "instruction": f"Perform {agent_configs.get(role)['task']}",
                        "params": {"topic": self.config.get("run_params", {}).get("topic", "General")}
                    })
            else:
                central_logger.log_interaction("System", "Debug", "No task sequence for synchronous mode")
            return workflow

    def register_tasks(self):
        """Register writing tasks."""
        register_task("plan_research", "Generate an article plan", plan_research)
        register_task("create_outline", "Create an article outline", create_outline)
        register_task("writer_task", "Draft the article", writer_task)
        register_task("editor_task", "Edit the draft", editor_task)
        register_task("finalize_article", "Finalize the article", finalize_article)
