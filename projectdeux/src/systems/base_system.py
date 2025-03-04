from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.custom_logging.central_logger import central_logger
from src.tasks.task_manager import TaskManager
from src.tasks.task_registry import TASK_REGISTRY
from src.tasks.async_task_manager import AsyncTaskManager

class BaseSystem(ABC):
    def __init__(
        self,
        agents,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        task_manager: Optional[TaskManager] = None,
        execution_type: str = "synchronous"
    ):
        self.agents = agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.config = config
        self.task_manager = task_manager or TaskManager()
        self.logger = central_logger
        self.goal = config.get("goal", "Solve a problem effectively")
        self.expected_result = config.get("expected_result", None)
        self.task_states: Dict[str, str] = {}
        self.system_type = self.__class__.__name__.lower().replace("system", "")
        self.execution_type = execution_type
        if self.execution_type == "asynchronous":
            self.async_task_manager = AsyncTaskManager()
        else:
            self.async_task_manager = None

    def get_agent_by_name(self, agent_name):
        """Retrieve an agent by name."""
        try:
            if isinstance(self.agents, dict):
                return self.agents.get(agent_name)
            return next(agent for agent in self.agents if agent.name == agent_name)
        except (StopIteration, AttributeError):
            return None

    def get_all_agents(self):
        """Return a list of all agent objects."""
        if isinstance(self.agents, dict):
            return list(self.agents.values())
        return self.agents

    @abstractmethod
    def define_workflow(self) -> List[Dict]:
        """Define the workflow."""
        pass

    def register_tasks(self):
        """Subclasses can override to register system-specific tasks."""
        pass

    def log_start(self, problem: str):
        """Log the start of the system run."""
        self.logger.log_system_start(
            system_name=self.__class__.__name__,
            entities=self.entity_manager.entities,
            problem=problem,
            goal=self.goal,
            expected_result=self.expected_result
        )

    def log_end(self, result: str, metadata: Dict, score: int):
        """Log the end of the system run."""
        all_agents = self.get_all_agents()
        self.logger.log_system_end(result, metadata, score, all_agents)

    def build_workflow_from_sequence(self, task_sequence: List[str], agent_configs: List[Dict]) -> List[Dict]:
        """
        Build a workflow from a predefined or supervisor-provided task sequence and agent configurations.

        Notes:
            - For asynchronous tasks, we now pass `agent.system_prompt` instead of `agent.id` to allow
              Celery tasks to recreate temporary agents.
        """
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
                    queue = config.get("queue", "celery")
                    # Use system_prompt instead of agent.id for Celery compatibility
                    args = [agent.system_prompt, topic, scenario_data] if i == 0 else [agent.system_prompt]
                    task_config = {"task_name": task_name, "args": args, "queue": queue, "agent_name": config["name"]}
                    workflow.append(task_config)
                else:
                    self.logger.warning(f"Agent '{config['name']}' not found for role '{role}'")
            else:
                self.logger.warning(f"No agent config found for role '{role}'")
        return workflow

    def run_workflow(self, workflow: List[Dict]) -> Dict:
        """
        Execute the workflow based on execution_type.

        Notes:
            - For asynchronous execution, we pass the `system_prompt` instead of the agent object or ID,
              enabling tasks to create temporary agents internally. This avoids serialization issues
              with Celery.
        """
        if self.execution_type == "asynchronous":
            task_list = []
            scenario_data = {
                "agent_names": {agent.id: agent.name for agent in self.get_all_agents()},
                "system_prompts": {agent.name: agent.system_prompt for agent in self.get_all_agents()},
                "context": {}
            }
            for i, task_config in enumerate(workflow):
                task_name = task_config["task_name"]
                agent_name = task_config["agent_name"]
                agent = self.get_agent_by_name(agent_name)
                if not agent:
                    raise ValueError(f"Agent '{agent_name}' not found.")
                task_func = TASK_REGISTRY[task_name]["function"]
                queue = task_config.get("queue", "default")
                # Pass system_prompt instead of agent.id for temporary agent creation in tasks
                if i == 0:
                    args = [None, agent.system_prompt, scenario_data]
                else:
                    args = [agent.system_prompt]
                task_list.append((task_func, args, queue))

            async_result = self.async_task_manager.dispatch_workflow(task_list)
            final_result = self.async_task_manager.get_task_result(async_result, timeout=60)

            if isinstance(final_result, tuple) and len(final_result) >= 2:
                result, scenario_data = final_result[:2]
                logs = final_result[2] if len(final_result) > 2 else []
            else:
                result, scenario_data, logs = final_result, {}, []

            for log in logs:
                self.logger.log_interaction(sender=log["from"], receiver=log["to"], message=log["message"])
            return {"final_result": result, "scenario_data": scenario_data, "logs": logs}

        elif self.execution_type == "synchronous":
            results = {}
            scenario_data = {
                "agent_names": {agent.id: agent.name for agent in self.get_all_agents()},
                "system_prompts": {agent.name: agent.system_prompt for agent in self.get_all_agents()},
                "context": {}
            }
            logs = []
            for task_config in workflow:
                task_name = task_config["task_name"]
                agent_name = task_config["agent_name"]
                agent = self.get_agent_by_name(agent_name)
                if not agent:
                    raise ValueError(f"Agent '{agent_name}' not found.")
                task_func = TASK_REGISTRY[task_name]["function"]
                if not results:
                    result, scenario_data = task_func(None, agent, scenario_data)
                else:
                    prev_result = list(results.values())[-1]
                    result, scenario_data = task_func((prev_result, scenario_data), agent)
                results[f"{task_name}_{agent_name}"] = result
            return {"final_result": results, "scenario_data": scenario_data, "logs": logs}

        else:
            raise ValueError(f"Invalid execution type: {self.execution_type}")

    def run(self, **kwargs):
        """Execute the system's workflow."""
        self.log_start(kwargs.get("problem", "Unnamed problem"))
        self.register_tasks()
        workflow = self.define_workflow()
        results = self.run_workflow(workflow)
        self.log_end(str(results["final_result"]), metadata={"tasks": len(workflow)}, score=100)
        return results