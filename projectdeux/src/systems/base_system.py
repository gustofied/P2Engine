# projectdeux/src/systems/base_system.py

from typing import Dict, List, Optional
from celery.result import AsyncResult
from celery import chain
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.custom_logging.central_logger import central_logger
from src.agents.factory import AgentFactory
from src.tasks.celery_task_manager import CeleryTaskManager
from src.tasks.celery_tasks import TASK_REGISTRY  # For chain usage

class BaseSystem:
    def __init__(self, config: Dict, entity_manager: Optional[EntityManager] = None, 
                 component_manager: Optional[ComponentManager] = None, 
                 task_manager: Optional[CeleryTaskManager] = None):
        self.config = config
        self.entity_manager = entity_manager or EntityManager()
        self.component_manager = component_manager or ComponentManager()
        self.task_manager = task_manager or CeleryTaskManager(agent_configs=config.get("agents", []))
        self.logger = central_logger
        self.agents = self._initialize_agents()
        self.goal = config.get("goal", "Solve a problem effectively")
        self.scenario_data = {
            "system_prompts": {agent["name"]: agent["system_prompt"] for agent in self.config.get("agents", [])},
            "agent_names": {agent["name"]: agent["name"] for agent in self.config.get("agents", [])}
        }

    def _initialize_agents(self) -> List:
        agents = []
        for agent_config in self.config.get("agents", []):
            agent = AgentFactory.create_agent(
                entity_manager=self.entity_manager,
                component_manager=self.component_manager,
                config=agent_config
            )
            agents.append(agent)
        return agents

    def execute_task(self, task_name: str, agent_name: str, **kwargs):
        """
        Wrapper that calls into the CeleryTaskManager to queue a task.
        Returns a queued message containing the Celery task ID.
        """
        return self.task_manager.execute_task(task_name, agent_name, **kwargs)

    def log_interaction(self, sender: str, receiver: str, message: str):
        """
        Simple helper to log interactions in the CentralLogger.
        """
        self.logger.log_interaction(sender, receiver, message)

    def run(self, **kwargs):
        """
        Run through the scenario's tasks.
        
        If the scenario defines two tasks and the second task has a parameter
        "text" equal to "{previous_result}", use a Celery chain so that the output
        of the first task is automatically passed as input to the second.
        
        Otherwise, queue tasks individually.
        """
        problem = self.config.get("problem", "No problem specified")
        entities = {agent.name: agent for agent in self.agents}
        
        # Log system start
        self.logger.log_system_start(
            system_name=self.__class__.__name__,
            entities=entities,
            problem=problem,
            goal=self.goal
        )
        
        tasks = self.config.get("tasks", [])
        results = {}

        # Check for chain condition: two tasks and second task's text parameter is "{previous_result}"
        if (len(tasks) == 2 and 
            tasks[1].get("params", {}).get("text") == "{previous_result}"):
            # Build a chain: first task (plan_research) then summarize_task.
            # For the first task, pass its parameters normally.
            first_task = TASK_REGISTRY.get(tasks[0]["task_name"])["function"].s(
                tasks[0]["agent_name"],
                **tasks[0].get("params", {}),
                scenario_data=self.scenario_data
            )
            # For the second task, we do not pass the "text" parameter—
            # the chain output (i.e. the plan) will be used as the 'text' argument.
            second_task = TASK_REGISTRY.get(tasks[1]["task_name"])["function"].s(
                tasks[1]["agent_name"],
                scenario_data=self.scenario_data
            )
            # Create the chain: plan_research -> summarize_task.
            # (Optionally, if plan_research returns a tuple, consider inserting a helper
            # to extract the first element; here we assume it returns the text directly.)
            chain_result = chain(first_task, second_task)()
            try:
                final_output = chain_result.get(timeout=120)
                # final_output should be the result of summarize_task.
                results = {
                    tasks[0]["task_name"]: "Chained task output not individually logged",
                    tasks[1]["task_name"]: final_output
                }
                self.logger.log_interaction("System", "Chain", f"Chain executed successfully. Final output: {final_output}")
            except TimeoutError:
                results = {"chain_result": "Chained tasks timed out"}
                self.log_interaction("System", "System", "Chained tasks timed out while waiting for result")
        else:
            # Fallback: queue tasks individually.
            task_ids = {}
            for task in tasks:
                agent_name = task["agent_name"]
                task_name = task["task_name"]
                params = task.get("params", {})

                queued_message = self.execute_task(
                    task_name,
                    agent_name,
                    scenario_data=self.scenario_data,
                    **params
                )
                # Parse out the Celery task ID from the returned string
                task_id = queued_message.split("ID=")[1].split(")")[0]
                task_ids[task_name] = task_id
                results[task_name] = queued_message  # Initially store the 'queued' message
                self.log_interaction("System", agent_name, f"Queued {task_name}: {queued_message}")

            # Wait for tasks & fetch results
            for task_name, task_id in task_ids.items():
                async_res = AsyncResult(task_id)
                try:
                    # Wait up to 60 seconds per task
                    task_result = async_res.get(timeout=60)
                    if isinstance(task_result, tuple) and len(task_result) >= 2:
                        text_output, interactions = task_result[0], task_result[1]
                        results[task_name] = text_output
                        for interaction in interactions:
                            self.logger.log_interaction(
                                sender=interaction["from"],
                                receiver=interaction["to"],
                                message=interaction["message"]
                            )
                    else:
                        results[task_name] = task_result
                except TimeoutError:
                    results[task_name] = f"Task {task_name} timed out"
                    self.log_interaction("System", "System", f"Task {task_name} timed out while waiting for result")
        
        # Log system end
        all_success = all(
            (isinstance(r, str) and "timed out" not in r) 
            or not isinstance(r, str)
            for r in results.values()
        )
        reward = 10 if all_success else 0
        self.logger.log_system_end(
            result=results,
            evaluation={"success": all_success},
            reward=reward,
            all_agents=entities
        )
        return results
