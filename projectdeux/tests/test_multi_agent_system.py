import time
from multi_agent_systems.multi_agent_scenario import multi_agent_conversation
from multi_agent_systems.multi_agent_scenario2 import multi_agent_conversation2
from multi_agent_systems.goal_scenario import run_enhanced_scenario

def test_multi_agent():
    run_enhanced_scenario()
    # multi_agent_conversation2()
    # This simple test runs the multi-agent conversation and prints outputs.
    # You can add assertions based on expected output patterns.

if __name__ == "__main__":
    test_multi_agent()
