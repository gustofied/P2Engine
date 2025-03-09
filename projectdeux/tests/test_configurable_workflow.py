import os
from src.systems.generic_system import GenericSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.systems.event_system import Event

def test_configurable_workflow():
    # Setup with test_scenario.yaml
    config_path = os.path.join(os.path.dirname(__file__), "../src/config/test_scenario.yaml")
    em = EntityManager()
    cm = ComponentManager()
    config = {}
    run_id = "test_run"
    system = GenericSystem(
        config_path=config_path,
        entity_manager=em,
        component_manager=cm,
        config=config,
        run_id=run_id
    )
    agent = system.spawn_agent("TestAgent")

    # Simulate a user message
    agent.process_event(Event("UserMessageEvent", "Hello"))

    # Step 1: Should be in UserMessage
    assert isinstance(agent.interaction_stack[-1], system.state_registry.get_state_class("UserMessage"))

    # Step 2: Tick to transition to AssistantMessage
    system.tick()
    assert isinstance(agent.interaction_stack[-1], system.state_registry.get_state_class("AssistantMessage"))

    # Step 3: Tick to transition to Finished
    system.tick()
    assert isinstance(agent.interaction_stack[-1], system.state_registry.get_state_class("Finished"))