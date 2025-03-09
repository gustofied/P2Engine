# src/tasks/task_manager.py
from typing import List, Dict, Optional
from src.agents.base_agent import BaseAgent

class TaskManager:
    def __init__(self):
        """Initialize the TaskManager with task registry, state tracking, and result caching."""
        self.tasks: Dict[str, Dict] = {}           # Registered tasks
        self.task_states: Dict[str, str] = {}      # Tracks state: "pending", "active", "completed"
        self.task_results: Dict[str, str] = {}     # Cache for task execution results

    def register_task(self, task_name: str, agents: List['src.agents.base_agent.BaseAgent'], instruction: str, 
                      dependencies: List[str] = None, required_params: List[str] = None,
                      dependency_params: Dict[str, str] = None):
        """Register a task with its agents, instruction, and dependencies."""
        self.tasks[task_name] = {
            "agents": agents,
            "instruction": instruction,
            "dependencies": dependencies or [],
            "required_params": required_params or [],
            "dependency_params": dependency_params or {}
        }
        self.task_states[task_name] = "pending"

    def execute_task(self, task_name: str, **kwargs):
        """Execute a task, handling dependencies and caching results."""
        # Return cached result if the task has already been executed
        if task_name in self.task_results:
            return self.task_results[task_name]

        # Verify the task exists
        task = self.tasks.get(task_name)
        if not task:
            raise ValueError(f"Task '{task_name}' not found")

        self.task_states[task_name] = "active"

        # Execute dependencies and collect their outputs
        dependency_outputs = {}
        for dep in task["dependencies"]:
            dep_task = self.tasks.get(dep)
            if not dep_task:
                raise ValueError(f"Dependency '{dep}' not found")
            # Pass only the parameters required by the dependency from the current kwargs
            dep_kwargs = {k: v for k, v in kwargs.items() if k in dep_task["required_params"]}
            response = self.execute_task(dep, **dep_kwargs)
            param_name = task["dependency_params"].get(dep, dep)
            dependency_outputs[param_name] = response

        # Combine provided kwargs with dependency outputs
        task_kwargs = {**kwargs, **dependency_outputs}

        # Check for missing required parameters
        missing_params = [param for param in task["required_params"] if param not in task_kwargs]
        if missing_params:
            raise ValueError(f"Missing parameters for '{task_name}': {missing_params}")

        # Format the instruction with the combined kwargs
        instruction = task["instruction"].format(**task_kwargs)

        # Execute the task with the appropriate agent(s)
        if len(task["agents"]) == 1:
            response = task["agents"][0].interact(instruction)
        else:
            responses = [agent.interact(instruction) for agent in task["agents"]]
            response = self.coordinate_responses(responses, task_name)

        self.task_states[task_name] = "completed"
        # Cache the result before returning
        self.task_results[task_name] = response
        return response

    def coordinate_responses(self, responses: List[str], task_name: str) -> str:
        """Coordinate responses from multiple agents into a single output."""
        valid_responses = [r.strip() for r in responses if r.strip()]
        if not valid_responses:
            return f"All agents returned empty responses for task '{task_name}'."
        summary = f"Coordinated Responses for '{task_name}':\n"
        for i, response in enumerate(valid_responses, 1):
            preview = response[:100] + ("..." if len(response) > 100 else "")
            summary += f"- Agent {i}: {preview}\n"
        return summary

    def get_task_state(self, task_name: str) -> Optional[str]:
        """Retrieve the current state of a task."""
        return self.task_states.get(task_name)