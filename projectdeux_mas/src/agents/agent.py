from src.components.components import StateComponent, ModelComponent
from src.systems.systems import EventProcessorSystem

def start_agent():
    agent_id = "1"
    queue_name = f"agent.{agent_id}.events"
    
    # Create entity for the agent
    entity = {
        "id": agent_id,
        "components": {
            "state": StateComponent(),
            "model": ModelComponent(model="openrouter/qwen/qwq-32b:free")  # Configurable per agent
        }
    }
    
    # Start the event processor system
    event_processor = EventProcessorSystem(agent_id, queue_name)
    try:
        event_processor.start(entity)
    except KeyboardInterrupt:
        print("Agent stopped.")