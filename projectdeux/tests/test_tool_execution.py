import os
from src.systems.generic_system import GenericSystem
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.systems.event_system import Event

def test_sub_agent_workflow():
    # Setup
    em = EntityManager()
    cm = ComponentManager()
    config = {}
    config_path = os.path.join(os.path.dirname(__file__), "../src/config/scenario.yaml")
    session = GenericSystem(
        config_path=config_path,
        entity_manager=em,
        component_manager=cm,
        config=config,
        run_id="test_run"
    )
    root_agent = session.spawn_agent("Root")

    # Step 1: Send user message to spawn sub-agent
    root_agent.process_event(Event("UserMessageEvent", "spawn Helper Perform a task"))

    # Step 2: Process UserMessage -> AssistantMessage
    session.tick()
    assert isinstance(root_agent.interaction_stack[-1], session.state_registry.get_state_class("AssistantMessage"))

    # Step 3: Process AssistantMessage -> AgentCall
    session.tick()
    assert isinstance(root_agent.interaction_stack[-1], session.state_registry.get_state_class("AgentCall"))

    # Step 4: Spawn sub-agent and transition to WaitingForAgentResult
    session.tick()
    assert isinstance(root_agent.interaction_stack[-1], session.state_registry.get_state_class("WaitingForAgentResult"))
    assert len(session.agents) == 2
    sub_agent = session.agents[1]
    assert sub_agent.parent == root_agent
    assert isinstance(sub_agent.interaction_stack[-1], session.state_registry.get_state_class("Finished"))
    assert sub_agent.interaction_stack[-1].result == "Completed task: Perform a task"

    # Step 5: Root agent receives AgentResultEvent and transitions to AgentResult
    session.tick()
    assert isinstance(root_agent.interaction_stack[-1], session.state_registry.get_state_class("AgentResult"))
    assert root_agent.interaction_stack[-1].result == "Completed task: Perform a task"

    # Step 6: Root AgentResult -> AssistantMessage
    session.tick()
    assert isinstance(root_agent.interaction_stack[-1], session.state_registry.get_state_class("AssistantMessage"))
    assert root_agent.interaction_stack[-1].response == "Completed task: Perform a task"