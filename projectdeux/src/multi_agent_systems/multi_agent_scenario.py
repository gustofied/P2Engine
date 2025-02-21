from single_agents.simple_agent.agent import SimpleAgent
from single_agents.chaos_agent.agent import ChaosAgent
import time

def multi_agent_conversation():
    # Initialize agents with their unique IDs.
    simple_agent = SimpleAgent(agent_id="SimpleAgent")
    chaos_agent = ChaosAgent(agent_id="ChaosAgent")
    
    # Round 1: SimpleAgent asks a question.
    prompt1 = "Hello, Chaos! How do you perceive the balance between order and chaos?"
    response1 = simple_agent.interact(prompt1)
    print("SimpleAgent says:", response1)
    time.sleep(1)  # Simulate delay
    
    # Round 2: ChaosAgent responds to SimpleAgent.
    response2 = chaos_agent.interact(response1)
    print("ChaosAgent replies:", response2)
    time.sleep(1)
    
    # Round 3: SimpleAgent responds back to ChaosAgent.
    response3 = simple_agent.interact(response2)
    print("SimpleAgent responds:", response3)
    
if __name__ == "__main__":
    multi_agent_conversation()
