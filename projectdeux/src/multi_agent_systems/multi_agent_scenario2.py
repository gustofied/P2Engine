import os
import time
import logging
from dotenv import load_dotenv
from custom_logging.simple_logger import log_message  # Our simple logger

load_dotenv()

from single_agents.simple_agent.agent import SimpleAgent
from single_agents.chaos_agent.agent import ChaosAgent
from single_agents.critic_agent.agent import CriticAgent  # Import our new critic agent

class MultiAgentSystem:
    def __init__(self, agents, rounds=10, delay=1, evaluation_interval=3):
        self.agents = agents
        self.rounds = rounds
        self.delay = delay
        self.evaluation_interval = evaluation_interval  # How often to call the CriticAgent
        self.conversation_history = ""
        self.logger = logging.getLogger(__name__)

    def log(self, message):
        print(message)
        logging.info(message)

    def run_conversation(self, initial_prompt):
        current_message = initial_prompt
        agent_index = 0

        # Create a critic agent instance.
        critic_agent = CriticAgent()  # Use your API key as needed

        for round_number in range(1, self.rounds + 1):
            sender_agent = self.agents[agent_index]
            # Determine receiver dynamically (next agent in the list).
            receiver_agent = self.agents[(agent_index + 1) % len(self.agents)]

            self.log(f"Round {round_number} - {sender_agent.name}'s turn (id: {sender_agent.id}).")
            self.log(f"Input: {current_message}")

            try:
                response = sender_agent.interact(current_message)
            except Exception as e:
                response = f"Error during interaction: {e}"
                self.log(response)

            self.log(f"{sender_agent.name} replied: {response}\n")
            
            # Append this exchange to the conversation history.
            self.conversation_history += f"{sender_agent.name} -> {receiver_agent.name}: {response}\n"

            # Log the message using the simple logger.
            log_message(sender=sender_agent.name, receiver=receiver_agent.name, text=response)

            # At evaluation intervals, have the CriticAgent analyze the conversation.
            if round_number % self.evaluation_interval == 0:
                self.log("Evaluating conversation progress with CriticAgent...")
                critic_feedback = critic_agent.interact(self.conversation_history)
                self.log(f"CriticAgent feedback: {critic_feedback}")
                # Check critic's feedback for hints to add a new agent.
                if "new agent" in critic_feedback.lower() or "create" in critic_feedback.lower():
                    # For illustration, we create a new SimpleAgent.
                    new_agent_name = "NewAgent"
                    new_agent = SimpleAgent(name=new_agent_name, model="gpt-3.5-turbo")
                    self.agents.append(new_agent)
                    self.log(f"New agent added dynamically: {new_agent.name}")
            
            current_message = response
            agent_index = (agent_index + 1) % len(self.agents)
            time.sleep(self.delay)

        self.log("Conversation ended.\n")
        return self.conversation_history

def multi_agent_conversation2():
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Instantiate initial agents.
    simple_agent = SimpleAgent(name="SimpleAgent", model="openai/gpt-4")
    chaos_agent = ChaosAgent(name="ChaosAgent", model="openai/gpt-3.5-turbo")
    agents = [simple_agent, chaos_agent]

    conversation_system = MultiAgentSystem(agents=agents, rounds=10, delay=1, evaluation_interval=3)

    initial_prompt = "Hello, Chaos! How do you perceive the balance between order and chaos?"
    history = conversation_system.run_conversation(initial_prompt)

    print("\nFinal Conversation History:")
    print(history)

if __name__ == "__main__":
    multi_agent_conversation2()
