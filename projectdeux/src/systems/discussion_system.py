from .base_system import BaseSystem
from src.tasks.task_registry import register_task
from typing import List, Dict

class DiscussionSystem(BaseSystem):
    def __init__(self, agents, entity_manager, component_manager, config, task_manager=None):
        super().__init__(
            agents=agents,
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=config,
            task_manager=task_manager,
            execution_type="asynchronous"
        )
        self.agents = {agent.name: agent for agent in agents}

    def define_workflow(self) -> List[Dict]:
        """Define the asynchronous workflow for the discussion system."""
        workflow = []
        task_sequence = self.config.get("task_sequence", [])
        task_description = self.config.get("problem", "")
        
        # Prepare scenario data for passing to tasks
        scenario_data = {
            "goal": self.goal,
            "problem": task_description,
            "system_prompts": {agent.name: agent.system_prompt for agent in self.agents.values()},
            "agent_names": {agent.id: agent.name for agent in self.agents.values()}
        }

        # Build the workflow based on the task sequence
        for i, agent_name in enumerate(task_sequence):
            agent = self.get_agent_by_name(agent_name)
            if agent.role == "summarizer":
                workflow.append({
                    "task_name": "summarize_discussion",
                    "args": [agent.id],
                    "queue": "summarizing_queue"
                })
            else:
                if i == 0:
                    # First task initializes the discussion
                    workflow.append({
                        "task_name": "generate_statement",
                        "args": [None, agent.id, task_description, scenario_data],
                        "queue": "discussion_queue"
                    })
                else:
                    # Subsequent tasks build on the previous output
                    workflow.append({
                        "task_name": "generate_statement",
                        "args": [agent.id],
                        "queue": "discussion_queue"
                    })
        return workflow

    def register_tasks(self):
        """Register discussion-specific tasks."""
        # Tasks are registered in task_registry.py, but this method can be used if needed
        pass