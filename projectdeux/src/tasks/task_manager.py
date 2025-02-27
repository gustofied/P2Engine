from typing import List, Dict, Optional
from agents.base_agent import BaseAgent

class TaskManager:
    def __init__(self):
        """Initialize the TaskManager with task registry and state tracking."""
        self.tasks: Dict[str, Dict] = {}
        self.task_states: Dict[str, str] = {}  # Tracks state: "pending", "active", "completed"

    def register_task(self, task_name: str, agents: List[BaseAgent], instruction: str, 
                      dependencies: List[str] = None, required_params: List[str] = None,
                      dependency_params: Dict[str, str] = None):
        """
        Register a task with one or more agents, instruction, dependencies, required parameters, 
        and dependency parameter mappings. Sets initial state to 'pending'.

        Args:
            task_name (str): Unique name of the task.
            agents (List[BaseAgent]): Agents responsible for executing the task.
            instruction (str): Instruction template with {param} placeholders.
            dependencies (List[str], optional): List of task names this task depends on.
            required_params (List[str], optional): Parameters required by the task.
            dependency_params (Dict[str, str], optional): Mapping of dependency outputs to parameter names.
        """
        self.tasks[task_name] = {
            "agents": agents,
            "instruction": instruction,
            "dependencies": dependencies or [],
            "required_params": required_params or [],
            "dependency_params": dependency_params or {}
        }
        self.task_states[task_name] = "pending"

    def execute_task(self, task_name: str, **kwargs):
        """
        Execute a task, updating its state and coordinating multi-agent responses if needed.

        Args:
            task_name (str): The task to execute.
            **kwargs: Task parameters.

        Returns:
            str: The task response.

        Raises:
            ValueError: If task, dependencies, or parameters are invalid.
        """
        task = self.tasks.get(task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")

        # Set task state to 'active'
        self.task_states[task_name] = "active"

        # Validate required parameters
        missing_params = [param for param in task["required_params"] if param not in kwargs]
        if missing_params:
            raise ValueError(f"Missing parameters for '{task_name}': {missing_params}")

        # Execute dependencies
        dependency_outputs = {}
        for dep in task["dependencies"]:
            dep_task = self.tasks.get(dep)
            if not dep_task:
                raise ValueError(f"Dependency '{dep}' not found")
            dep_kwargs = {k: v for k, v in kwargs.items() if k in dep_task["required_params"]}
            missing_dep_params = [p for p in dep_task["required_params"] if p not in dep_kwargs]
            if missing_dep_params:
                raise ValueError(f"Missing parameters for '{dep}': {missing_dep_params}")
            response = self.execute_task(dep, **dep_kwargs)
            param_name = task["dependency_params"].get(dep, dep)
            dependency_outputs[param_name] = response

        # Combine kwargs with dependency outputs
        task_kwargs = {**kwargs, **dependency_outputs}
        instruction = task["instruction"].format(**task_kwargs)

        # Execute with agents
        if len(task["agents"]) == 1:
            response = task["agents"][0].interact(instruction)
        else:
            responses = [agent.interact(instruction) for agent in task["agents"]]
            response = self.coordinate_responses(responses, task_name)

        # Set task state to 'completed'
        self.task_states[task_name] = "completed"
        return response

    def coordinate_responses(self, responses: List[str], task_name: str) -> str:
        """
        Coordinate responses from multiple agents for a task.

        Args:
            responses (List[str]): Responses from agents.
            task_name (str): Name of the task for context.

        Returns:
            str: A coordinated response.
        """
        if not responses:
            return f"No responses received for task '{task_name}'."

        # Enhanced coordination: prioritize non-empty responses and summarize
        valid_responses = [r.strip() for r in responses if r.strip()]
        if not valid_responses:
            return f"All agents returned empty responses for task '{task_name}'."

        summary = f"Coordinated Responses for '{task_name}':\n"
        for i, response in enumerate(valid_responses, 1):
            preview = response[:100] + ("..." if len(response) > 100 else "")
            summary += f"- Agent {i}: {preview}\n"
        return summary

    def get_task_state(self, task_name: str) -> Optional[str]:
        """Retrieve the state of a task."""
        return self.task_states.get(task_name)