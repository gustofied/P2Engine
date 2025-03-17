import aio_pika
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
import uuid
import json
import asyncio
from src.agents.base_agent import BaseAgent
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.custom_logging.central_logger import central_logger
from src.tasks.async_task_manager import AsyncTaskManager
from src.agents.factory import AgentFactory
from src.states.state_registry import StateRegistry
from src.integrations.artifact_store import ArtifactStore
from src.redis_client import redis_client
from celery import chain
from celery_app import app as celery_app
from src.tasks.task_definitions import process_agent_step, process_agent_event
from src.event import Event

class BaseSystem(ABC):
    session_instances = {}

    def __init__(
        self,
        agents: List[BaseAgent],
        entity_manager: EntityManager,
        component_manager: ComponentManager,
        config: Dict,
        run_id: Optional[str] = None,
        config_path: str = "test_scenario.yaml"
    ):
        """Initialize the BaseSystem with agents and configuration."""
        self.id = run_id if run_id is not None else str(uuid.uuid4())
        self.run_id = self.id
        self.agents = agents
        self.entity_manager = entity_manager
        self.component_manager = component_manager
        self.config = config
        self.async_task_manager = AsyncTaskManager(self.run_id)
        self.logger = central_logger
        self.config_path = config_path
        self.state_registry = StateRegistry(config_path)
        self.artifact_store = ArtifactStore(run_id=self.run_id)
        self.channel = None

        self.goal = config.get('goal', 'No goal specified')
        self.expected_result = config.get('expected_result', 'No expected result specified')

        for agent in self.agents:
            agent.session = self
            agent.state_registry = self.state_registry
            agent.run_id = self.run_id
            agent.subscribe("UserMessageEvent")

        BaseSystem.session_instances[self.id] = self
        self.logger.log_interaction(
            "System", "Init", f"Initialized BaseSystem with ID {self.id}", self.run_id
        )

    async def start_event_consumer(self):
        """Start consuming events from a RabbitMQ queue."""
        try:
            connection = await aio_pika.connect_robust("amqp://127.0.0.1/")
            self.channel = await connection.channel()
            queue_name = f"system_queue_{self.run_id}"
            queue = await self.channel.declare_queue(queue_name)
            await queue.consume(self.process_system_event)
        except Exception as e:
            self.logger.log_error(
                "BaseSystem", e, self.run_id, context={"action": "start_event_consumer"}
            )

    async def process_system_event(self, message: aio_pika.IncomingMessage):
        """Process incoming system events."""
        async with message.process():
            event_data = json.loads(message.body)
            event = Event(**event_data)
            self.handle_event(event)

    def handle_event(self, event: Event):
        """Handle a system event (to be implemented by subclasses)."""
        pass

    def publish(self, event: Event) -> List[str]:
        """Publish an event to subscribers via Celery tasks."""
        task_ids = []
        subscribers = redis_client.smembers(f"subscriptions:{event.type}") or set()
        print(f"Publishing event {event.type} to {len(subscribers)} subscribers")
        for subscriber in subscribers:
            entity_type, entity_id = subscriber.decode().split(":", 1)
            if entity_type == "agent":
                queue_name = f"agent_queue_{self.run_id}"
                print(f"Dispatching to queue: {queue_name}")
                result = process_agent_event.apply_async(
                    args=[entity_id, self.id, self.run_id, event.to_dict()],
                    queue=queue_name
                )
                task_ids.append(result.id)
            elif entity_type == "system" and entity_id == self.id:
                self.handle_event(event)
        return task_ids

    def subscribe(self, entity, event_type: str, correlation_id: Optional[str] = None) -> None:
        """Subscribe an entity to an event type."""
        key = f"subscriptions:{event_type}"
        value = f"agent:{entity.id}" if entity != self else f"system:{self.id}"
        redis_client.sadd(key, value)
        self.logger.log_interaction(
            entity.name if entity != self else "System", "System",
            f"Subscribed to {event_type}", self.run_id
        )

    def unsubscribe(self, entity, event_type: str) -> None:
        """Unsubscribe an entity from an event type."""
        key = f"subscriptions:{event_type}"
        value = f"agent:{entity.id}" if entity != self else f"system:{self.id}"
        redis_client.srem(key, value)
        self.logger.log_interaction(
            entity.name if entity != self else "System", "System",
            f"Unsubscribed from {event_type}", self.run_id
        )

    def spawn_agent(self, agent_type: str, parent: "BaseAgent" = None, correlation_id: str = None):
        """Spawn a new agent dynamically."""
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
            state_registry=self.state_registry,
            run_id=self.run_id
        )
        agent.parent = parent
        agent.correlation_id = correlation_id
        self.agents.append(agent)
        redis_client.set(f"agent_config:{agent.id}", json.dumps(config))
        self.logger.log_interaction(
            "System", agent.name,
            f"Spawned as sub-agent of {parent.name if parent else 'None'}", self.run_id
        )
        return agent

    def tick(self) -> List[str]:
        """Execute a single step for all agents."""
        task_ids = []
        for agent in self.agents:
            queue_name = f"agent_queue_{self.run_id}"
            task = process_agent_step.apply_async(
                args=[agent.id, self.id, self.run_id],
                queue=queue_name
            )
            task_ids.append(task.id)
        self.logger.log_interaction("System", "Tick", "Dispatched agent steps", self.run_id)
        return task_ids

    @abstractmethod
    def define_workflow(self) -> List[Dict]:
        """Define the workflow for the system (must be implemented by subclasses)."""
        pass

    def log_start(self, problem: str):
        """Log the start of the system execution."""
        self.logger.log_system_start(
            system_name=self.__class__.__name__,
            entities=self.entity_manager.entities,
            problem=problem,
            goal=self.goal,
            expected_result=self.expected_result
        )

    def log_end(self, result: str, metadata: Dict, score: int):
        """Log the end of the system execution."""
        all_agents = self.get_all_agents()
        self.logger.log_system_end(result, metadata, score, all_agents)

    def build_workflow_from_sequence(self, task_sequence: List[Dict]) -> List[Dict]:
        """Build a workflow from a sequence of tasks."""
        from src.tasks.task_registry import TASK_REGISTRY
        workflow = []
        scenario_data = {
            "goal": self.goal,
            "problem": self.config.get("problem", "No problem defined"),
            "system_prompts": {agent.name: agent.system_prompt for agent in self.get_all_agents()},
            "agent_names": {agent.id: agent.name for agent in self.get_all_agents()},
            "run_params": self.config.get("run_params", {}),
            "context": {},
            "run_id": self.run_id
        }

        for i, task_config in enumerate(task_sequence):
            agent = self.get_agent_by_name(task_config["agent_name"])
            if agent:
                task_func = TASK_REGISTRY["generic_task"]["function"]
                queue = task_config.get("queue", f"agent_queue_{self.run_id}")
                args = [None, agent.system_prompt, task_config, scenario_data] if i == 0 else [agent.system_prompt, task_config]
                workflow.append({
                    "task_func": task_func,
                    "args": args,
                    "queue": queue,
                    "task_config": task_config
                })
            else:
                self.logger.log_interaction(
                    "System", "WorkflowBuilder",
                    f"Agent '{task_config['agent_name']}' not found", self.run_id
                )
        return workflow

    def run_workflow(self, workflow: List[Dict]) -> Dict:
        """Execute the workflow using Celery tasks."""
        celery_tasks = [task["task_func"].s(*task["args"]).set(queue=task["queue"]) for task in workflow]
        full_chain = chain(*celery_tasks)
        async_result = full_chain()
        final_result = self.async_task_manager.get_task_result(async_result, timeout=120)
        result, scenario_data = final_result[:2]
        logs = final_result[2] if len(final_result) > 2 else []
        for log in logs:
            self.logger.log_interaction(log["from"], log["to"], log["message"], self.run_id)
        return {"final_result": result, "scenario_data": scenario_data, "logs": logs}

    def run(self, **kwargs):
        """Run the system with the defined workflow."""
        self.log_start(kwargs.get("problem", "Unnamed problem"))
        workflow = self.define_workflow()
        built_workflow = self.build_workflow_from_sequence(workflow)
        results = self.run_workflow(built_workflow)
        self.log_end(str(results["final_result"]), metadata={"tasks": len(workflow)}, score=100)
        return results

    def get_agent_by_name(self, agent_name):
        """Retrieve an agent by its name."""
        try:
            return next(agent for agent in self.agents if agent.name == agent_name)
        except StopIteration:
            return None

    def get_all_agents(self):
        """Return all agents in the system."""
        return self.agents