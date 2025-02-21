import time
import logging

# Import the two agent classes.
from single_agents.simple_agent.agent import SimpleAgent
from single_agents.chaos_agent.agent import ChaosAgent

class MultiAgentSystem:
    """
    A comprehensive multi-agent conversation system that cycles through agents,
    logging the conversation, handling errors, and storing conversation history.
    """
    def __init__(self, agents, rounds=10, delay=1):
        """
        Initialize the multi-agent system.
        
        :param agents: List of agent instances.
        :param rounds: Total number of conversation rounds.
        :param delay: Delay (in seconds) between rounds.
        """
        self.agents = agents
        self.rounds = rounds
        self.delay = delay
        self.conversation_history = []  # List to store each round's details.

    def log(self, message):
        """
        Log a message to both the console and the logging system.
        
        :param message: The message string.
        """
        print(message)
        logging.info(message)

    def run_conversation(self, initial_prompt):
        """
        Run a multi-round conversation among agents, cycling through them.
        
        :param initial_prompt: The starting prompt for the conversation.
        :return: A list of dictionaries capturing the conversation history.
        """
        current_message = initial_prompt
        agent_index = 0

        for round_number in range(1, self.rounds + 1):
            # Select the current agent in a round-robin fashion.
            agent = self.agents[agent_index]
            self.log(f"Round {round_number} - {agent.agent_id}'s turn.")
            self.log(f"Input: {current_message}")

            # Attempt to get the agent's response.
            try:
                response = agent.interact(current_message)
            except Exception as e:
                response = f"Error during interaction: {e}"
                self.log(response)

            self.log(f"{agent.agent_id} replied: {response}\n")
            self.conversation_history.append({
                'round': round_number,
                'agent': agent.agent_id,
                'input': current_message,
                'response': response
            })

            # Set up for the next round.
            current_message = response
            agent_index = (agent_index + 1) % len(self.agents)
            time.sleep(self.delay)

        self.log("Conversation ended.\n")
        return self.conversation_history

def     multi_agent_conversation2():
    # Configure logging to include timestamps and log level.
    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s - %(levelname)s - %(message)s')

    # Initialize the agents with unique IDs.
    simple_agent = SimpleAgent(agent_id="SimpleAgent")
    chaos_agent = ChaosAgent(agent_id="ChaosAgent")
    agents = [simple_agent, chaos_agent]

    # Set up the multi-agent system: adjust rounds and delay as needed.
    conversation_system = MultiAgentSystem(agents=agents, rounds=10, delay=1)

    # Begin the conversation with an initial prompt.
    initial_prompt = "Hello, Chaos! How do you perceive the balance between order and chaos?"
    history = conversation_system.run_conversation(initial_prompt)

    # Print the complete conversation history.
    print("\nFinal Conversation History:")
    for record in history:
        print(f"Round {record['round']} - {record['agent']} was given: {record['input']}")
        print(f"Round {record['round']} - {record['agent']} replied: {record['response']}\n")

if __name__ == "__main__":
    multi_agent_conversation2()
