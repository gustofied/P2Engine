from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.custom_logging.central_logger import central_logger
from src.tasks.task_manager import TaskManager
from src.tasks.task_registry import TASK_REGISTRY
from src.tasks.async_task_manager import AsyncTaskManager
from celery import chain

class BaseSystem(ABC):
    """
    Abstract base class for defining and executing a system workflow.
    Supports both synchronous and asynchronous task execution using Celery.
    """
    def __init__(
        self,
        agents,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        task_manager: Optional[TaskManager] = None,
        execution_type: str = "synchronous"
    ):
        """
        Initialize the BaseSystem with agents, managers, and configuration.

        Args:
            agents: List or dict of agent objects.
            entity_manager: Manages entities in the system.
            component_manager: Manages components in the system.
            config: Configuration dictionary for the system.
            task_manager: Optional custom TaskManager instance.
            execution_type: 'synchronous' or 'asynchronous' execution mode.
        """
        self.agents = agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.config = config
        self.task_manager = task_manager or TaskManager()
        self.logger = central_logger
        self.goal = config.get("goal", "Solve a problem effectively")
        self.expected_result = config.get("expected_result", None)
        self.execution_type = execution_type
        if self.execution_type == "asynchronous":
            self.async_task_manager = AsyncTaskManager()
        else:
            self.async_task_manager = None

    def get_agent_by_name(self, agent_name):
        """Retrieve an agent by its name."""
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
        """Define the workflow as a list of task configurations. Must be implemented by subclasses."""
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

    def build_workflow_from_sequence(self, task_sequence: List[Dict]) -> List[Dict]:
        """
        Build a workflow from a predefined task sequence provided in the config.
        Each task in the sequence includes 'task_name', 'agent_name', 'instruction', and 'params'.

        Args:
            task_sequence: List of task configuration dictionaries.

        Returns:
            List of workflow steps with task functions and arguments.
        """
        workflow = []
        scenario_data = {
            "goal": self.goal,
            "problem": self.config.get("problem", "No problem defined"),
            "system_prompts": {agent.name: agent.system_prompt for agent in self.get_all_agents()},
            "agent_names": {agent.id: agent.name for agent in self.get_all_agents()},
            "run_params": self.config.get("run_params", {}),
            "context": {}
        }
        for i, task_config in enumerate(task_sequence):
            agent = self.get_agent_by_name(task_config["agent_name"])
            if agent:
                task_func = TASK_REGISTRY["generic_task"]["function"]
                queue = task_config.get("queue", "default")
                # For the first task, include None as previous_output
                if i == 0:
                    args = [None, agent.system_prompt, task_config, scenario_data]
                # For subsequent tasks, omit previous_output (Celery will provide it in async mode)
                else:
                    args = [agent.system_prompt, task_config, scenario_data]
                workflow.append({
                    "task_func": task_func,
                    "args": args,
                    "queue": queue,
                    "task_config": task_config
                })
            else:
                self.logger.warning(f"Agent '{task_config['agent_name']}' not found")
        return workflow

    def run_workflow(self, workflow: List[Dict]) -> Dict:
        """
        Execute the workflow based on the execution type.

        Args:
            workflow: List of task dictionaries with functions and arguments.

        Returns:
            Dictionary containing the final result, scenario data, and logs.
        """
        if self.execution_type == "asynchronous":
            # Build a Celery chain of tasks
            celery_tasks = []
            for task in workflow:
                task_func = task["task_func"]
                args = task["args"]
                queue = task["queue"]
                celery_task = task_func.s(*args).set(queue=queue)
                celery_tasks.append(celery_task)
            full_chain = chain(*celery_tasks)
            async_result = full_chain()
            final_result = self.async_task_manager.get_task_result(async_result, timeout=120)
            result, scenario_data = final_result[:2]
            logs = final_result[2] if len(final_result) > 2 else []
            for log in logs:
                self.logger.log_interaction(sender=log["from"], receiver=log["to"], message=log["message"])
            return {"final_result": result, "scenario_data": scenario_data, "logs": logs}

        elif self.execution_type == "synchronous":
            # Execute tasks sequentially, passing output to the next task
            results = {}
            previous_output = None
            for task in workflow:
                task_func = task["task_func"]
                task_config = task["task_config"]
                agent = self.get_agent_by_name(task_config["agent_name"])
                if previous_output is None:
                    # Use initial args for the first task
                    args = task["args"]  # [None, agent.system_prompt, task_config, scenario_data]
                else:
                    # Use previous output for subsequent tasks
                    scenario_data = previous_output[1]  # Update scenario_data
                    args = [previous_output, agent.system_prompt, task_config, scenario_data]
                previous_output = task_func(*args)
                result, scenario_data = previous_output  # Unpack the result tuple
                results[task_config["task_name"]] = result
            return {"final_result": results, "scenario_data": scenario_data, "logs": []}

        else:
            raise ValueError(f"Invalid execution type: {self.execution_type}")

    def run(self, **kwargs):
        """Execute the system's workflow and log the process."""
        self.log_start(kwargs.get("problem", "Unnamed problem"))
        workflow = self.define_workflow()
        built_workflow = self.build_workflow_from_sequence(workflow)
        results = self.run_workflow(built_workflow)
        self.log_end(str(results["final_result"]), metadata={"tasks": len(workflow)}, score=100)
        return results