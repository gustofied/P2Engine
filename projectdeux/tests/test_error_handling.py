import os
from src.systems.generic_system import GenericSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.systems.event_system import Event

def test_error_handling():
    # Setup
    config_path = os.path.join(os.path.dirname(__file__), "../src/config/scenario.yaml")
    em = EntityManager()
    cm = ComponentManager()
    config = {}
    run_id = "test_run_error"
    session = GenericSystem(
        config_path=config_path,
        entity_manager=em,
        component_manager=cm,
        config=config,
        run_id=run_id
    )
    agent = session.spawn_agent("TestAgent")

    # Step 1: Trigger tool call
    agent.process_event(Event("UserMessageEvent", "use test_tool"))
    session.tick()  # UserMessage -> AssistantMessage
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("AssistantMessage"))

    # Step 2: Transition to ToolCall
    session.tick()
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("ToolCall"))

    # Step 3: Simulate tool failure
    agent.pending_events.append(Event("ToolFailureEvent", "Simulated tool failure"))
    session.tick()
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("ErrorState"))

    # Step 4: Verify retry
    session.tick()
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("AssistantMessage"))

    # Step 5: Simulate failure again to stop
    agent.pending_events.append(Event("ToolFailureEvent", "Simulated tool failure again"))
    session.tick()  # Processes ToolCallEvent -> ToolCall
    session.tick()  # Processes ToolFailureEvent -> ErrorState, appends StopEvent
    session.tick()  # Processes StopEvent -> Finished
    assert isinstance(agent.interaction_stack[-1], session.state_registry.get_state_class("Finished"))