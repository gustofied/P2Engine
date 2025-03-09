from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import uuid
from agents.base_agent import BaseAgent
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.custom_logging.central_logger import central_logger
from src.tasks.task_manager import TaskManager
from src.systems.event_system import EventQueue
from src.agents.factory import AgentFactory
from src.states.state_registry import StateRegistry

class BaseSystem(ABC):
    session_instances = {}  # Class-level dictionary to track sessions

    def __init__(
        self,
        agents: List,
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        run_id: Optional[str] = None,
        task_manager: Optional[TaskManager] = None,
        config_path: str = "scenario.yaml"  # New parameter for scenario.yaml
    ):
        self.id = run_id or str(uuid.uuid4())
        self.run_id = self.id
        self.agents = agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.config = config
        self.task_manager = task_manager or TaskManager()
        self.logger = central_logger
        self.event_queue = EventQueue()
        self.config_path = config_path  # Store config path
        self.state_registry = StateRegistry(config_path)  # Initialize StateRegistry

        # Set goal and expected_result from config with defaults
        self.goal = config.get('goal', 'No goal specified')
        self.expected_result = config.get('expected_result', 'No expected result specified')

        # Assign session to agents
        for agent in self.agents:
            agent.session = self
            agent.state_registry = self.state_registry  # Pass StateRegistry to existing agents

        BaseSystem.session_instances[self.id] = self

    def spawn_agent(self, agent_type: str, parent: "BaseAgent" = None, correlation_id: str = None):
        """Spawn a new agent using AgentFactory with StateRegistry."""
        config = {
            "name": f"{agent_type}_{uuid.uuid4()}",
            "system_prompt": f"Agent type: {agent_type}",
            "role": agent_type
        }
        agent = AgentFactory.create_agent(
            entity_manager=self.entity_manager,
            component_manager=self.component_manager,
            config=config,
            session=self,
            state_registry=self.state_registry  # Pass StateRegistry
        )
        agent.parent = parent
        agent.correlation_id = correlation_id
        self.agents.append(agent)
        self.logger.log_interaction("System", agent.name, f"Spawned as sub-agent of {parent.name if parent else 'None'}")
        return agent

    @abstractmethod
    def define_workflow(self) -> List[Dict]:
        pass

    def tick(self):
        """Simulate one cycle of the event loop."""
        self.event_queue.dispatch()
        for agent in self.agents:
            agent.step()

    # Other methods (get_agent_by_name, get_all_agents, etc.) remain unchanged

    # ... (other methods like get_all_agents, run, etc., remain unchanged)

    def get_agent_by_name(self, agent_name):
        try:
            if isinstance(self.agents, dict):
                return self.agents.get(agent_name)
            return next(agent for agent in self.agents if agent.name == agent_name)
        except (StopIteration, AttributeError):
            return None

    def get_all_agents(self):
        if isinstance(self.agents, dict):
            return list(self.agents.values())
        return self.agents

    @abstractmethod
    def define_workflow(self) -> List[Dict]:
        pass

    def log_start(self, problem: str):
        self.logger.log_system_start(
            system_name=self.__class__.__name__,
            entities=self.entity_manager.entities,
            problem=problem,
            goal=self.goal,
            expected_result=self.expected_result
        )

    def log_end(self, result: str, metadata: Dict, score: int):
        all_agents = self.get_all_agents()
        self.logger.log_system_end(result, metadata, score, all_agents)

    def build_workflow_from_sequence(self, task_sequence: List[Dict]) -> List[Dict]:
        # Local import to avoid circular dependency
        from src.tasks.task_registry import TASK_REGISTRY

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
                # The function from TASK_REGISTRY
                task_func = TASK_REGISTRY["generic_task"]["function"]

                queue = task_config.get("queue", "default")

                # For first task, pass None as "previous_output"
                if i == 0:
                    args = [None, agent.system_prompt, task_config, scenario_data]
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
        """Execute the tasks either asynchronously with Celery or synchronously."""
        if self.execution_type == "asynchronous":
            celery_tasks = []
            for task in workflow:
                task_func = task["task_func"]
                args = task["args"]
                queue = task["queue"]
                # Build the Celery signature
                celery_task = task_func.s(*args).set(queue=queue)
                celery_tasks.append(celery_task)

            # Chain them in sequence
            full_chain = chain(*celery_tasks)
            async_result = full_chain()
            final_result = self.async_task_manager.get_task_result(async_result, timeout=120)

            result, scenario_data = final_result[:2]
            logs = final_result[2] if len(final_result) > 2 else []

            # If logs were captured, store them
            for log in logs:
                self.logger.log_interaction(sender=log["from"], receiver=log["to"], message=log["message"])

            return {"final_result": result, "scenario_data": scenario_data, "logs": logs}

        elif self.execution_type == "synchronous":
            results = {}
            previous_output = None

            for i, task in enumerate(workflow):
                task_func = task["task_func"]
                task_config = task["task_config"]
                agent = self.get_agent_by_name(task_config["agent_name"])

                # For first task, pass None as "previous_output"
                if i == 0:
                    args = task["args"]
                else:
                    # subsequent tasks get the previous output
                    scenario_data = previous_output[1]
                    args = [previous_output, agent.system_prompt, task_config, scenario_data]

                # Execute the task
                previous_output = task_func(*args)
                result, scenario_data = previous_output
                results[task_config["task_name"]] = result

            return {"final_result": results, "scenario_data": scenario_data, "logs": []}

        else:
            raise ValueError(f"Invalid execution type: {self.execution_type}")

    def run(self, **kwargs):
        """Convenience method to start the workflow and log results."""
        self.log_start(kwargs.get("problem", "Unnamed problem"))
        workflow = self.define_workflow()
        built_workflow = self.build_workflow_from_sequence(workflow)
        results = self.run_workflow(built_workflow)
        self.log_end(str(results["final_result"]), metadata={"tasks": len(workflow)}, score=100)
        return results
