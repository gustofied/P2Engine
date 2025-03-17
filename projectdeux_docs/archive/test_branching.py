import os
import pytest
from src.systems.generic_system import GenericSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.systems.event_system import Event
from src.redis_client import redis_client as REDIS_CLIENT

def test_branching(config_path, unique_run_id, celery_worker, wait_for_tasks):
    """
    Test the branching behavior of the GenericSystem, ensuring sub-agents are spawned correctly.
    """
    # Setup
    em = EntityManager()
    cm = ComponentManager()
    session = GenericSystem(
        config_path=config_path,
        entity_manager=em,
        component_manager=cm,
        config={},
        run_id=unique_run_id
    )
    agent = session.spawn_agent("RootAgent")

    # Subscribe to UserMessageEvent
    session.event_queue.subscribe(agent, "UserMessageEvent")

    # Trigger branching with an event
    session.event_queue.publish(Event("UserMessageEvent", "explore multiple options"))
    task_ids = session.tick(asynchronous=True)  # Process UserMessageEvent
    wait_for_tasks(task_ids)
    task_ids = session.tick(asynchronous=True)  # AgentCall publishes SpawnAgentEvents
    wait_for_tasks(task_ids)
    task_ids = session.tick(asynchronous=True)  # Process SpawnAgentEvents
    wait_for_tasks(task_ids)

    # Verify sub-agents are created
    assert len(session.agents) == 3, f"Expected 3 agents (root + 2 sub-agents), got {len(session.agents)}"
    sub_agent1, sub_agent2 = session.agents[1], session.agents[2]
    assert sub_agent1.parent == agent, "Sub-agent 1 parent mismatch"
    assert sub_agent2.parent == agent, "Sub-agent 2 parent mismatch"
    assert sub_agent1.correlation_id == sub_agent2.correlation_id, "Correlation IDs should match"

    # Simulate sub-agent completion
    for _ in range(3):
        task_ids = session.tick(asynchronous=True)
        wait_for_tasks(task_ids)

    # Check final state
    assert any(isinstance(state, session.state_registry.get_state_class("AgentResult"))
               for state in agent.interaction_stack), "AgentResult state not reached"

    # Explicit Redis cleanup (optional, as cleanup fixture handles this)
    REDIS_CLIENT.delete(f"agent_config:{agent.id}")
    REDIS_CLIENT.delete(f"subscriptions:{agent.id}")