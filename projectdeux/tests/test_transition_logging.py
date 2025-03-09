import os
from src.systems.generic_system import GenericSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.systems.event_system import Event
from src.custom_logging.central_logger import central_logger
def test_transition_logging():
    # Setup: Initialize a GenericSystem and spawn an agent
    config_path = os.path.join(os.path.dirname(__file__), "../src/config/scenario.yaml")
    em = EntityManager()
    cm = ComponentManager()
    config = {}
    run_id = "test_run_transition_logging"
    session = GenericSystem(
        config_path=config_path,
        entity_manager=em,
        component_manager=cm,
        config=config,
        run_id=run_id
    )
    agent = session.spawn_agent("TestAgent")

    # Start logging for the system
    session.log_start(problem="Test transition logging")

    # Step 1: Trigger a UserMessageEvent
    agent.process_event(Event("UserMessageEvent", "Hello"))

    # Step 2: Process the event and transition to AssistantMessage
    session.tick()
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("AssistantMessage")), \
        "Expected transition to AssistantMessage failed"

    # Step 3: Verify logs for expected and successful transition
    logs = central_logger.get_logs()
    interactions = logs.get("interactions", [])
    assert any(
        "Expected transition: UserMessage -> AssistantMessage with event None" in interaction["message"]
        for interaction in interactions
    ), "Expected transition log not found"
    assert any(
        "Transition successful: UserMessage -> AssistantMessage" in interaction["message"]
        for interaction in interactions
    ), "Successful transition log not found"

    print("Transition logging test passed!")