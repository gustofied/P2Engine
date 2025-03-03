from celery import shared_task
from src.custom_logging.central_logger import central_logger
from src.agents.base_agent import BaseAgent
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
import datetime
import os
from dotenv import load_dotenv
import logging

load_dotenv()
logger = logging.getLogger(__name__)

TASK_REGISTRY = {}

def register_task(task_name: str, description: str, func):
    """Register a task in the global registry."""
    TASK_REGISTRY[task_name] = {
        "description": description,
        "function": func
    }

@shared_task
def tell_joke(previous_output, agent_or_prompt, initial_scenario_data: dict = None):
    """
    Tell a joke, compatible with both synchronous and asynchronous execution.

    Args:
        previous_output: The result from the previous task in an async chain, or None if first task.
        agent_or_prompt: Either a string (system_prompt for async mode) or a BaseAgent object (for sync mode).
        initial_scenario_data (dict, optional): Initial data for the scenario, used if first task.

    Raises:
        ValueError: If agent_or_prompt is neither a string nor a BaseAgent object.

    Notes:
        - In asynchronous mode, a temporary BaseAgent is created using the provided system_prompt.
        - In synchronous mode, the provided BaseAgent object is used directly.
    """
    if isinstance(agent_or_prompt, str):
        # Asynchronous mode: Create a temporary agent
        entity_manager = EntityManager()
        component_manager = ComponentManager()
        temp_agent = BaseAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="TempAgent",
            system_prompt=agent_or_prompt
        )
    elif isinstance(agent_or_prompt, BaseAgent):
        # Synchronous mode: Use provided agent directly
        temp_agent = agent_or_prompt
    else:
        raise ValueError("agent_or_prompt must be a string or BaseAgent object")

    if previous_output is None:  # First task in chain or sync mode
        scenario_data = initial_scenario_data or {}
        scenario_data.setdefault("context", {}).setdefault("jokes", [])
    else:  # Subsequent task in async chain
        _, scenario_data = previous_output

    user_input = "Tell a one-sentence joke."
    result = temp_agent.interact(user_input)
    scenario_data["context"]["jokes"].append({"agent": temp_agent.name, "joke": result})
    
    central_logger.log_interaction("System", temp_agent.name, f"Told joke: {result}")
    
    return (result, scenario_data)

@shared_task
def react_to_jokes(previous_output, agent_or_prompt):
    """
    React to jokes, expecting previous_output from an async chain or sync input.

    Args:
        previous_output: Tuple containing the previous task's result and scenario data.
        agent_or_prompt: Either a string (system_prompt for async mode) or a BaseAgent object (for sync mode).

    Raises:
        ValueError: If agent_or_prompt is neither a string nor a BaseAgent object.

    Notes:
        - In asynchronous mode, a temporary BaseAgent is created using the provided system_prompt.
        - In synchronous mode, the provided BaseAgent object is used directly.
    """
    if isinstance(agent_or_prompt, str):
        # Asynchronous mode: Create a temporary agent
        entity_manager = EntityManager()
        component_manager = ComponentManager()
        temp_agent = BaseAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="TempAgent",
            system_prompt=agent_or_prompt
        )
    elif isinstance(agent_or_prompt, BaseAgent):
        # Synchronous mode: Use provided agent directly
        temp_agent = agent_or_prompt
    else:
        raise ValueError("agent_or_prompt must be a string or BaseAgent object")

    result, scenario_data = previous_output
    jokes = scenario_data["context"].get("jokes", [])
    joke_text = ", ".join([j["joke"] for j in jokes])
    user_input = f"React briefly to these jokes: {joke_text}"
    reaction = temp_agent.interact(user_input)
    
    central_logger.log_interaction("System", temp_agent.name, f"Reacted: {reaction}")
    
    return (reaction, scenario_data)

@shared_task
def evaluate_jokes(previous_output, agent_or_prompt):
    """
    Evaluate all jokes and pick the best.

    Args:
        previous_output: Tuple containing the previous task's result and scenario data.
        agent_or_prompt: Either a string (system_prompt for async mode) or a BaseAgent object (for sync mode).

    Raises:
        ValueError: If agent_or_prompt is neither a string nor a BaseAgent object.

    Notes:
        - In asynchronous mode, a temporary BaseAgent is created using the provided system_prompt.
        - In synchronous mode, the provided BaseAgent object is used directly.
    """
    if isinstance(agent_or_prompt, str):
        # Asynchronous mode: Create a temporary agent
        entity_manager = EntityManager()
        component_manager = ComponentManager()
        temp_agent = BaseAgent(
            entity_manager=entity_manager,
            component_manager=component_manager,
            name="TempAgent",
            system_prompt=agent_or_prompt
        )
    elif isinstance(agent_or_prompt, BaseAgent):
        # Synchronous mode: Use provided agent directly
        temp_agent = agent_or_prompt
    else:
        raise ValueError("agent_or_prompt must be a string or BaseAgent object")

    result, scenario_data = previous_output
    jokes = scenario_data["context"].get("jokes", [])
    joke_text = ", ".join([f"{j['agent']}: {j['joke']}" for j in jokes])
    user_input = f"Evaluate these jokes and pick the best: {joke_text}"
    evaluation = temp_agent.interact(user_input)
    
    central_logger.log_interaction("System", temp_agent.name, f"Evaluation: {evaluation}")
    
    return (evaluation, scenario_data)

# Register the tasks
register_task("tell_joke", "Tell a one-sentence joke", tell_joke)
register_task("react_to_jokes", "React to other agents' jokes", react_to_jokes)
register_task("evaluate_jokes", "Evaluate and select the best joke", evaluate_jokes)