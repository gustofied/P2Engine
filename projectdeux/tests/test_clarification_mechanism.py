import os
from src.systems.generic_system import GenericSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.systems.event_system import Event
from src.custom_logging.central_logger import central_logger

def test_clarification_mechanism():
    # Setup: Initialize a GenericSystem and spawn an agent
    config_path = os.path.join(os.path.dirname(__file__), "../src/config/scenario.yaml")
    em = EntityManager()
    cm = ComponentManager()
    config = {}
    run_id = "test_run_clarification"
    session = GenericSystem(
        config_path=config_path,
        entity_manager=em,
        component_manager=cm,
        config=config,
        run_id=run_id
    )
    agent = session.spawn_agent("TestAgent")

    # Start logging for the system
    session.log_start(problem="Test clarification mechanism")

    # Step 1: Trigger a UserMessageEvent with an unrecognized command
    agent.process_event(Event("UserMessageEvent", "do something"))

    # Step 2: Process the event and transition to AssistantMessage
    session.tick()
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("AssistantMessage")), \
        "Expected transition to AssistantMessage failed"

    # Step 3: Process the ClarificationEvent and transition to ClarificationState
    session.tick()
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("ClarificationState")), \
        "Expected transition to ClarificationState failed"

    # Step 4: Verify logs for clarification request
    logs = central_logger.get_logs()
    interactions = logs.get("interactions", [])
    assert any(
        "Entering ClarificationState: asking for clarification" in interaction["message"]
        for interaction in interactions
    ), "Clarification log not found"

    # Step 5: Verify the clarification response event
    assert any(
        event.type == "ResponseReadyEvent" and event.payload == "I didn’t understand that. Could you please rephrase?"
        for event in agent.pending_events
    ), "Expected clarification response event not found"

    print("Clarification mechanism test passed, brah!")