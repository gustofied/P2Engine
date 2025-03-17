from celery_app import app
from src.custom_logging.central_logger import central_logger
from src.redis_client import redis_client
from src.agents.factory import AgentFactory
from src.event import Event
from redis.exceptions import LockError
import json
from typing import List, Dict

@app.task
def process_agent_event(agent_id: str, session_id: str, run_id: str, event_data: dict):
    """Process a specific event for an agent asynchronously.

    Args:
        agent_id (str): Unique identifier for the agent.
        session_id (str): Identifier for the session the agent belongs to.
        run_id (str): Unique identifier for the current run.
        event_data (dict): Data describing the event to process.
    """
    central_logger.log_interaction("Celery", "System", f"Starting task for agent {agent_id}", run_id)
    lock = redis_client.lock(f"agent_lock:{agent_id}", timeout=30)
    try:
        if lock.acquire(blocking=True, blocking_timeout=5):
            central_logger.log_interaction("Celery", "System", f"Acquired lock for agent {agent_id}", run_id)
        else:
            central_logger.log_interaction("Celery", "System", f"Failed to acquire lock for agent {agent_id}", run_id)
            return
        config_str = redis_client.get(f"agent_config:{agent_id}")
        if not config_str:
            central_logger.log_interaction("Celery", "System", f"Agent config for {agent_id} not found", run_id)
            return
        config = json.loads(config_str)

        from src.entities.entity_manager import EntityManager
        from src.entities.component_manager import ComponentManager
        from src.states.state_registry import StateRegistry

        entity_manager = EntityManager()
        component_manager = ComponentManager()
        config_path = config.get("config_path", "src/scenarios/test_scenario.yaml")
        state_registry = StateRegistry(config_path)

        agent = AgentFactory.create_agent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=config,
            state_registry=state_registry,
            run_id=run_id
        )
        agent.id = agent_id

        agent.load_state()
        event = Event(**event_data)
        agent.process_event(event)
        agent.step()
        agent.save_state()

        central_logger.log_interaction("Celery", agent.name, f"Processed event: {event.type}", run_id)
    except Exception as e:
        central_logger.log_interaction("Celery", "System", f"Error processing event for agent {agent_id}: {str(e)}", run_id)
        raise
    finally:
        try:
            lock.release()
            central_logger.log_interaction("Celery", "System", f"Released lock for agent {agent_id}", run_id)
        except LockError:
            central_logger.log_interaction("Celery", "System", f"Lock already released for agent {agent_id}", run_id)
        central_logger.log_interaction("Celery", "System", f"Completed task for agent {agent_id}", run_id)

@app.task
def process_agent_step(agent_id: str, session_id: str, run_id: str):
    """Process a step for an agent asynchronously using Redis for state management.

    Args:
        agent_id (str): Unique identifier for the agent.
        session_id (str): Identifier for the session the agent belongs to.
        run_id (str): Unique identifier for the current run.
    """
    central_logger.log_interaction("Celery", "System", f"Starting step for agent {agent_id}", run_id)
    lock = redis_client.lock(f"agent_lock:{agent_id}", timeout=30)
    try:
        if lock.acquire(blocking=True, blocking_timeout=5):
            central_logger.log_interaction("Celery", "System", f"Acquired lock for agent {agent_id}", run_id)
        else:
            central_logger.log_interaction("Celery", "System", f"Failed to acquire lock for agent {agent_id}", run_id)
            return
        config_str = redis_client.get(f"agent_config:{agent_id}")
        if not config_str:
            central_logger.log_interaction("Celery", "System", f"Agent config for {agent_id} not found", run_id)
            return
        config = json.loads(config_str)

        from src.entities.entity_manager import EntityManager
        from src.entities.component_manager import ComponentManager
        from src.states.state_registry import StateRegistry

        entity_manager = EntityManager()
        component_manager = ComponentManager()
        config_path = config.get("config_path", "src/scenarios/test_scenario.yaml")
        state_registry = StateRegistry(config_path)

        agent = AgentFactory.create_agent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            config=config,
            state_registry=state_registry,
            run_id=run_id
        )
        agent.id = agent_id

        agent.load_state()
        agent.step()
        agent.save_state()

        central_logger.log_interaction("Celery", agent.name, "Processed step", run_id)
    except Exception as e:
        central_logger.log_interaction("Celery", "System", f"Error processing step for agent {agent_id}: {str(e)}", run_id)
        raise
    finally:
        try:
            lock.release()
            central_logger.log_interaction("Celery", "System", f"Released lock for agent {agent_id}", run_id)
        except LockError:
            central_logger.log_interaction("Celery", "System", f"Lock already released for agent {agent_id}", run_id)
        central_logger.log_interaction("Celery", "System", f"Completed step for agent {agent_id}", run_id)

@app.task
def process_branch_task(agent_id: str, session_id: str, task: str, correlation_id: str, run_id: str):
    """Process a branch task for an agent asynchronously.

    Args:
        agent_id (str): Unique identifier for the agent.
        session_id (str): Identifier for the session the agent belongs to.
        task (str): The task description or content to process.
        correlation_id (str): Identifier to correlate this task with other events.
        run_id (str): Unique identifier for the current run.
    """
    central_logger.log_interaction("Celery", "System", f"Starting branch task for agent {agent_id}", run_id)
    from src.systems.base_system import BaseSystem
    session = BaseSystem.session_instances.get(session_id)
    if not session:
        central_logger.log_interaction("Celery", "System", f"Session {session_id} not found", run_id)
        return
    agent = next((a for a in session.agents if a.id == agent_id), None)
    if not agent:
        central_logger.log_interaction("Celery", "System", f"Agent {agent_id} not found", run_id)
        return
    event = Event("UserMessageEvent", task, correlation_id=correlation_id)
    session.publish(event)
    agent.process_event(event)
    agent.step()
    central_logger.log_interaction("Celery", agent.name, f"Processed branch task: {task}", run_id)

@app.task
def query_llm_task(model: str, api_key: str, messages: List[Dict], metadata: Dict, run_id: str) -> str:
    """Asynchronously query the LLM.

    Args:
        model (str): The LLM model to use.
        api_key (str): API key for accessing the LLM service.
        messages (List[Dict]): List of message dictionaries to send to the LLM.
        metadata (Dict): Additional metadata for the query.
        run_id (str): Unique identifier for the current run.

    Returns:
        str: The response from the LLM.
    """
    from src.integrations.llm.llm_client import LLMClient
    llm_client = LLMClient(model=model, api_key=api_key)
    response = llm_client.query(messages, metadata)
    central_logger.log_interaction("Celery", "LLM", f"Queried LLM: {response}", run_id)
    return response

@app.task
def execute_tool_task(tool_name: str, args: Dict, run_id: str) -> str:
    """Asynchronously execute a tool.

    Args:
        tool_name (str): Name of the tool to execute.
        args (Dict): Arguments to pass to the tool.
        run_id (str): Unique identifier for the current run.

    Returns:
        str: The result of the tool execution.
    """
    from src.integrations.tools.tool_registry import ToolRegistry
    tool_class = ToolRegistry.get(tool_name)
    if tool_class:
        tool = tool_class()
        result = tool.execute(**args)
        central_logger.log_interaction("Celery", "Tool", f"Executed tool {tool_name}: {result}", run_id)
        return str(result)
    else:
        central_logger.log_interaction("Celery", "System", f"Tool {tool_name} not found", run_id)
        return f"Tool {tool_name} not found"

@app.task
def add(x: int, y: int) -> int:
    """Simple addition task for testing.

    Args:
        x (int): First number.
        y (int): Second number.

    Returns:
        int: Sum of x and y.
    """
    return x + y