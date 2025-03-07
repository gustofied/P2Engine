from .base_system import BaseSystem
from src.agents.factory import AgentFactory
from src.custom_logging.central_logger import central_logger
from typing import List, Dict
from src.utils import start_celery_workers  # Import the utility function

class GenericSystem(BaseSystem):
    """A generic system that builds workflows from predefined sequences or supervisor decisions."""
    
    def __init__(self, agents, entity_manager, component_manager, config, task_manager=None, run_id=None):
        execution_type = config.get("execution_type", "synchronous")
        super().__init__(
            agents=agents,
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=config,
            task_manager=task_manager,
            execution_type=execution_type
        )
        self.agents = {agent.name: agent for agent in agents}
        self.run_id = run_id  # Store the run_id for queue uniqueness

    def define_workflow(self) -> List[Dict]:
        """Define the workflow based on config: either predefined or dynamic."""
        if "task_sequence" in self.config:
            workflow = self.config["task_sequence"]
            if self.execution_type != "synchronous":
                # Append run_id to queues for async scenarios
                for task in workflow:
                    task["queue"] = f"{task['queue']}_{self.run_id}"
            return workflow
        else:
            supervisor = next((agent for agent in self.agents.values() if agent.role == "supervisor"), None)
            if not supervisor:
                raise ValueError("No supervisor agent found for dynamic workflow")
            topic = self.config.get("run_params", {}).get("topic", "General")
            prompt = (
                f"You are planning a project on the topic: {topic}. "
                f"Task: '{self.config['problem']}'. "
                "Define agents with 'name', 'role', 'system_prompt'. "
                "Also, specify the 'task_sequence' as a list of {'task_name': task, 'agent_name': name, 'instruction': instruction, 'params': params}."
                "If execution is asynchronous, append the run_id to queue names, e.g., 'queue_name_{self.run_id}'."
                "Return JSON with 'agents' (array) and 'task_sequence'."
            )
            decision = supervisor.decide_agents(prompt)
            agent_configs = decision["agents"]
            workflow = decision["task_sequence"]
            for config in agent_configs:
                if config["name"] not in self.agents:
                    new_agent = AgentFactory.create_agent(
                        self.entity_manager, self.component_manager, config
                    )
                    self.agents[config["name"]] = new_agent
                    central_logger.log_interaction("System", "Debug", f"Created agent: {config['name']}")
            return workflow

    def run(self, **kwargs):
        self.log_start(kwargs.get("problem", "Unnamed problem"))
        workflow = self.define_workflow()
        
        if self.execution_type == "synchronous":
            # Synchronous execution: run directly without workers
            built_workflow = self.build_workflow_from_sequence(workflow)
            results = self.run_workflow(built_workflow)
        else:
            # Asynchronous execution: manage a worker dynamically
            # Use default queue if "queue" key is missing, appending run_id for uniqueness
            queues = set(task.get("queue", f"default_{self.run_id}") for task in workflow)
            worker_process = start_celery_workers(queues)
            try:
                built_workflow = self.build_workflow_from_sequence(workflow)
                results = self.run_workflow(built_workflow)
            finally:
                worker_process.terminate()
        
        self.log_end(str(results["final_result"]), metadata={"tasks": len(workflow)}, score=100)
        return results