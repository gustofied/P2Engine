from typing import Optional, List, Any
from single_agents.base_agent import BaseAgent

class SimpleAgent(BaseAgent):
    def __init__(
        self,
        name: str = "SimpleAgent",
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        tools: Optional[List[Any]] = None
    ):
        # Pass everything up to BaseAgent, including model choice
        super().__init__(name=name, model=model, api_key=api_key, tools=tools)

    def interact(self, user_input: str) -> str:
        metadata = {"agent_name": self.name, "agent_id": self.id}
        response = self.llm.query(user_input, metadata=metadata)
        return f"{self.name}: {response}"

if __name__ == "__main__":
    # Local test. If no API key is given, we look for OPENAI_API_KEY in .env or your environment.
    agent = SimpleAgent()
    print(agent.interact("Tell me a joke."))
