import time
from single_agents.simple_agent.agent import SimpleAgent

def test_multiple_calls():
    agent = SimpleAgent(agent_id="TestAgent")
    for i in range(3):
        response = agent.interact(f"Test message {i}")
        print(f"Response {i}: {response}")
        time.sleep(1)  # simulate delay between calls

if __name__ == "__main__":
    test_multiple_calls()
