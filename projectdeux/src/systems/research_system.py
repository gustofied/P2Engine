# src/systems/research_system.py
from .base_system import BaseSystem
from src.tasks.task_registry import register_task, plan_research, collect_data, analyze_data, TASK_REGISTRY
from src.agents.factory import AgentFactory
from src.custom_logging.central_logger import central_logger
from src.agents.supervisor_agent import SupervisorAgent
from typing import Dict, List

class ResearchSystem(BaseSystem):
    def __init__(
        self,
        agents,
        entity_manager,
        component_manager,
        config: Dict,
        task_manager=None,
        execution_type: str = "synchronous"
    ):
        super().__init__(
            agents=agents,
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=config,
            task_manager=task_manager,
            execution_type=execution_type
        )

    def define_workflow(self) -> List[Dict]:
        if "task_sequence" in self.config:
            task_sequence = self.config["task_sequence"]
            agent_configs = self.config["agents"]
            role_to_agent = {agent["role"]: agent for agent in agent_configs}
            workflow = []
            previous_task = None
            for role in task_sequence:
                agent_config = role_to_agent.get(role)
                if agent_config:
                    task_name = agent_config["task"]
                    instruction = f"Perform {task_name} for research on {{topic}}"
                    if task_name == "plan_research":
                        instruction = "Generate a research plan for the topic: {topic}"
                    elif task_name == "collect_data":
                        instruction = "Collect data based on the research plan: {output_from_previous}" if previous_task else "Collect data on {topic}"
                    elif task_name == "analyze_data":
                        instruction = "Analyze the collected data: {output_from_previous}" if previous_task else "Analyze data on {topic}"
                    
                    workflow.append({
                        "task_name": task_name,
                        "agent_name": agent_config["name"],
                        "instruction": instruction,
                        "params": {"topic": self.config.get("run_params", {}).get("topic", "General")},
                        "dependencies": [previous_task] if previous_task else [],
                        "required_params": ["output_from_previous"] if previous_task else ["topic"],
                        "dependency_params": {previous_task: "output_from_previous"} if previous_task else {}
                    })
                    previous_task = task_name
            return workflow
        else:
            # Corrected line: iterate directly over self.agents (list) instead of self.agents.values()
            supervisor = next((agent for agent in self.agents if isinstance(agent, SupervisorAgent)), None)
            if not supervisor:
                raise ValueError("No supervisor agent found.")
            
            # Construct prompt with available tasks
            available_tasks = ", ".join(TASK_REGISTRY.keys())
            prompt = (
                f"You are an AI assistant planning a {self.system_type} project. "
                f"The task is: '{self.config['problem']}'. "
                "Determine which specialized AI agents are needed. "
                "Each agent should have a 'name', 'role', 'task', 'queue', and 'system_prompt'. "
                f"The 'task' must be one of the following: {available_tasks}. "
                "Also, specify the 'task_sequence' (list of role names) for execution order. "
                "Return a JSON object with 'agents' (array of agent configs) and 'task_sequence'."
                "\n\nExample response:\n```json\n"
                "{\n  \"agents\": [\n    {\"name\": \"PlanBot\", \"role\": \"planner\", \"task\": \"plan_research\", \"queue\": \"planning_queue\", \"system_prompt\": \"Plan the research.\"},\n"
                "    {\"name\": \"DataBot\", \"role\": \"collector\", \"task\": \"collect_data\", \"queue\": \"data_queue\", \"system_prompt\": \"Collect data.\"}\n  ],\n"
                "  \"task_sequence\": [\"planner\", \"collector\"]\n}\n```"
            )
            decision = supervisor.decide_agents(prompt)
            
            # Validate tasks
            for agent_config in decision["agents"]:
                task_name = agent_config["task"]
                if task_name not in TASK_REGISTRY:
                    raise ValueError(f"Task '{task_name}' is not registered in TASK_REGISTRY")
            
            task_sequence = decision["task_sequence"]
            agent_configs = decision["agents"]
            for config in agent_configs:
                if config["name"] not in [agent.name for agent in self.agents]:
                    self.agents.append(AgentFactory.create_agent(
                        entity_manager=self.entity_manager,
                        component_manager=self.component_manager,
                        config=config
                    ))
            role_to_agent = {agent["role"]: agent for agent in agent_configs}
            workflow = []
            previous_task = None
            for role in task_sequence:
                agent_config = role_to_agent.get(role)
                if agent_config:
                    task_name = agent_config["task"]
                    instruction = f"Perform {task_name} for research on {{topic}}"
                    if task_name == "plan_research":
                        instruction = "Generate a research plan for the topic: {topic}"
                    elif task_name == "collect_data":
                        instruction = "Collect data based on the research plan: {output_from_previous}" if previous_task else "Collect data on {topic}"
                    elif task_name == "analyze_data":
                        instruction = "Analyze the collected data: {output_from_previous}" if previous_task else "Analyze data on {topic}"
                    
                    workflow.append({
                        "task_name": task_name,
                        "agent_name": agent_config["name"],
                        "instruction": instruction,
                        "params": {"topic": self.config.get("run_params", {}).get("topic", "General")},
                        "dependencies": [previous_task] if previous_task else [],
                        "required_params": ["output_from_previous"] if previous_task else ["topic"],
                        "dependency_params": {previous_task: "output_from_previous"} if previous_task else {}
                    })
                    previous_task = task_name
            return workflow

    def register_tasks(self):
        register_task("plan_research", "Plan the research", plan_research)
        register_task("collect_data", "Collect research data", collect_data)
        register_task("analyze_data", "Analyze collected data", analyze_data)