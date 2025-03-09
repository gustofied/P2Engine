import os
from src.systems.generic_system import GenericSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.systems.event_system import Event
from src.custom_logging.central_logger import central_logger

def test_state_refactor():
    # Setup
    config_path = os.path.join(os.path.dirname(__file__), "../src/config/scenario.yaml")
    em = EntityManager()
    cm = ComponentManager()
    config = {}
    run_id = "test_run_state_refactor"
    session = GenericSystem(
        config_path=config_path,
        entity_manager=em,
        component_manager=cm,
        config=config,
        run_id=run_id
    )
    agent = session.spawn_agent("TestAgent")

    # Log system start
    session.log_start(problem="Test state transitions after refactor")

    # Step 1: Process a user message
    agent.process_event(Event("UserMessageEvent", "use test_tool"))
    session.tick()  # UserMessage -> AssistantMessage
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("AssistantMessage")), "Failed to transition to AssistantMessage"

    # Step 2: Simulate tool call
    session.tick()  # AssistantMessage -> ToolCall
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("ToolCall")), "Failed to transition to ToolCall"

    # Step 3: Simulate tool failure
    agent.pending_events.append(Event("ToolFailureEvent", {"error": "Simulated tool failure"}, correlation_id="test_corr_id"))
    session.tick()  # ToolCall -> ToolFailureState
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("ToolFailureState")), "Failed to transition to ToolFailureState"

    # Step 4: Verify logs
    logs = central_logger.get_logs()
    interactions = logs.get("interactions", [])
    assert any(
        "Entered ToolFailureState: Simulated tool failure" in interaction["message"]
        for interaction in interactions
    ), "Tool failure log not found"

    # Step 5: Simulate retry
    agent.pending_events.append(Event("RetryEvent", None))
    session.tick()  # ToolFailureState -> AssistantMessage
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("AssistantMessage")), "Failed to retry to AssistantMessage"

    print("State refactor test passed!")