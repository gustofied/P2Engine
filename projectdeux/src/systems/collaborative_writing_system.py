# src/systems/collaborative_writing_system.py
from .base_system import BaseSystem
from src.agents.supervisor_agent import SupervisorAgent
from celery import chain

class CollaborativeWritingSystem(BaseSystem):
    def run(self, **kwargs):
        """Execute the collaborative writing workflow."""
        problem = self.config["problem"]
        self.logger.info(f"Starting collaborative writing for: {problem}")
        domain = kwargs.get("domain", "General")

        # Find the supervisor
        supervisor = next((a for a in self.agents if isinstance(a, SupervisorAgent)), None)
        if not supervisor:
            raise ValueError("No supervisor agent found")

        # Plan tasks
        decision = supervisor.decide_agents(problem)
        task_sequence = decision["task_sequence"]

        # Execute initial task
        initial_role = task_sequence[0]
        agent = next(a for a in self.agents if a.role == initial_role)
        initial_result = self.execute_task(
            task_name=agent.task_name,  # Assume agents have a task_name
            agent_name=agent.name,
            domain=domain,
            problem=problem
        )

        # Adapt and chain remaining tasks
        adapted_sequence = supervisor.adapt_agents(f"Refine based on: {initial_result}", self)
        remaining_tasks = []
        for role in adapted_sequence[1:]:  # Skip initial role
            agent = next(a for a in self.agents if a.role == role)
            task = self.execute_task(
                task_name=agent.task_name,
                agent_name=agent.name,
                previous_result=initial_result
            )
            remaining_tasks.append(task)

        final_result = chain(*remaining_tasks)().get(timeout=500)
        self.logger.info(f"Completed writing: {final_result}")
        return final_result