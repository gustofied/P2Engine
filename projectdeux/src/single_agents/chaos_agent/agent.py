from integrations.llm.llm_client import LLMClient
from custom_logging.litellm_logger import my_custom_logging_fn
from single_agents.base_agent import BaseAgent

class ChaosAgent(BaseAgent):
    def __init__(self, agent_id: str = "ChaosAgent", model: str = "gpt-3.5-turbo", api_key: str = None):
        self.agent_id = agent_id
        # For standard calls we could use LLMClient, but here we need to prepend a system prompt.
        self.api_key = api_key
        # Create a base LLMClient instance to reuse parameters.
        self.llm_client = LLMClient(model=model, api_key=api_key, logger_fn=my_custom_logging_fn)
        # Define a creative, strange system prompt.
        self.system_prompt = (
            "You are Chaos: unpredictable, creative, and cryptic. "
            "Respond in bizarre metaphors, whimsical riddles, and surreal imagery."
        )

    def interact(self, user_input: str) -> str:
        """
        Send a system prompt and then the user input to generate a chaotic response.
        """
        # Build a messages list including a system prompt.
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]
        # Instead of using LLMClient.query (which only accepts a single user message),
        # we directly call litellm.completion with our multi‑message list.
        import litellm
        response = litellm.completion(
            model=self.llm_client.model,
            messages=messages,
            api_key=self.llm_client.api_key,
            logger_fn=self.llm_client.logger_fn,
            metadata={"agent_id": self.agent_id}
        )
        return response["choices"][0]["message"]["content"]

if __name__ == "__main__":
    # Quick local test for ChaosAgent.
    agent = ChaosAgent()
    print("ChaosAgent test response:", agent.interact("What is the meaning of unpredictability?"))
