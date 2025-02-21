from dotenv import load_dotenv
load_dotenv()  # Load environment variables from the .env file.

# Optionally, you could enable litellm's built-in debugging if needed.
# But to rely solely on file logging, we keep it disabled.
# import litellm
# litellm._turn_on_debug()

from integrations.llm.llm_client import LLMClient
from custom_logging.litellm_logger import my_custom_logging_fn
from single_agents.base_agent import BaseAgent  # Assume an abstract BaseAgent is defined

class SimpleAgent(BaseAgent):
    def __init__(self, agent_id: str = "SimpleAgent", model: str = "gpt-3.5-turbo", api_key: str = None):
        self.agent_id = agent_id
        # Pass our custom logger to the LLMClient.
        self.llm = LLMClient(model=model, api_key=api_key, logger_fn=my_custom_logging_fn)

    def interact(self, user_input: str) -> str:
        # Prepare metadata including the agent's identity.
        metadata = {"agent_id": self.agent_id}
        response = self.llm.query(user_input, metadata=metadata)
        return f"SimpleAgent: {response}"

if __name__ == "__main__":
    agent = SimpleAgent()  # API key loaded from OPENAI_APY_KEY in .env.
    print(agent.interact("Tell me a joke."))
