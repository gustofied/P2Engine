import os
import time
import logging
from dotenv import load_dotenv

load_dotenv()

from single_agents.simple_agent.agent import SimpleAgent
from single_agents.chaos_agent.agent import ChaosAgent

class MultiAgentSystem:
    def __init__(self, agents, rounds=10, delay=1):
        self.agents = agents
        self.rounds = rounds
        self.delay = delay
        self.conversation_history = []

    def log(self, message):
        print(message)
        logging.info(message)

    def run_conversation(self, initial_prompt):
        current_message = initial_prompt
        agent_index = 0

        for round_number in range(1, self.rounds + 1):
            agent = self.agents[agent_index]
            self.log(f"Round {round_number} - {agent.name}'s turn (id: {agent.id}).")
            self.log(f"Input: {current_message}")

            try:
                response = agent.interact(current_message)
            except Exception as e:
                response = f"Error during interaction: {e}"
                self.log(response)

            self.log(f"{agent.name} replied: {response}\n")

            self.conversation_history.append({
                'round': round_number,
                'agent': agent.name,
                'agent_id': agent.id,
                'input': current_message,
                'response': response
            })

            current_message = response
            agent_index = (agent_index + 1) % len(self.agents)
            time.sleep(self.delay)

        self.log("Conversation ended.\n")
        return self.conversation_history

def multi_agent_conversation():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Each agent picks its own model
    simple_agent = SimpleAgent(name="SimpleAgent", model="text-davinci-003")
    chaos_agent = ChaosAgent(name="ChaosAgent", model="gpt-3.5-turbo")
    agents = [simple_agent, chaos_agent]

    conversation_system = MultiAgentSystem(agents=agents, rounds=10, delay=1)

    initial_prompt = "Hello, Chaos! How do you perceive the balance between order and chaos?"
    history = conversation_system.run_conversation(initial_prompt)

    print("\nFinal Conversation History:")
    for record in history:
        print(f"Round {record['round']} - {record['agent']} (id: {record['agent_id']}) was given: {record['input']}")
        print(f"Round {record['round']} - {record['agent']} replied: {record['response']}\n")

if __name__ == "__main__":
    multi_agent_conversation()
