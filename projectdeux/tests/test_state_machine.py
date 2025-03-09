import os
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.agents.base_agent import BaseAgent
from src.systems.event_system import Event
from src.config.state_registry import StateRegistry

def test_state_machine():
    # Setup
    em = EntityManager()
    cm = ComponentManager()
    config_path = os.path.join(os.path.dirname(__file__), "../src/config/test_scenario.yaml")
    state_registry = StateRegistry(config_path)
    agent = BaseAgent(
        entity_manager=em,
        component_manager=cm,
        name="TestAgent",
        state_registry=state_registry
    )

    # Simulate user message event
    agent.process_event(Event("UserMessageEvent", "Hello"))

    # Step 1: UserMessage -> AssistantMessage
    agent.step()
    assert isinstance(agent.interaction_stack[-1], state_registry.get_state_class("AssistantMessage")), "Expected AssistantMessage state"

    # Step 2: AssistantMessage -> Finished
    agent.step()
    assert isinstance(agent.interaction_stack[-1], state_registry.get_state_class("Finished")), "Expected Finished state"