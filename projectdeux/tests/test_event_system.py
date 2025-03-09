import os
import uuid
from src.entities.entity_manager import EntityManager
from src.entities.component_manager import ComponentManager
from src.systems.generic_system import GenericSystem
from src.systems.event_system import Event

def test_event_system():
    # Create managers
    em = EntityManager()
    cm = ComponentManager()

    # Define config
    config = {
        "execution_type": "synchronous",
        "task_sequence": [],
    }
    run_id = str(uuid.uuid4())
    config_path = os.path.join(os.path.dirname(__file__), "../src/config/scenario.yaml")

    # Create system
    system = GenericSystem(
        config_path=config_path,
        entity_manager=em,
        component_manager=cm,
        config=config,
        run_id=run_id
    )

    # Spawn agent
    agent = system.spawn_agent("TestAgent")

    # Verify session link
    assert agent.session == system, "Agent's session should match the system instance"

    # Subscribe agent to event
    system.event_queue.subscribe(agent, "TestEvent")

    # Publish and dispatch event
    event = Event("TestEvent", "Hello, world!")
    system.event_queue.publish(event)
    system.event_queue.dispatch()

    # Check event reception
    assert len(agent.pending_events) == 1, "Agent should have one pending event"
    assert agent.pending_events[0].type == "TestEvent", "Event type should be TestEvent"
    assert agent.pending_events[0].payload == "Hello, world!", "Payload should match"