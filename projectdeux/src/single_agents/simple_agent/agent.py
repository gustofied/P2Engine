from typing import Optional, List, Any
from single_agents.base_agent import BaseAgent

class SimpleAgent(BaseAgent):
    def __init__(
        self,
        name: str = "SimpleAgent",
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        tools: Optional[List[Any]] = None,
        system_prompt: str = "You are a helpful and concise assistant"
    ):
        super().__init__(
            name=name,
            model=model,
            api_key=api_key,
            tools=tools,
            system_prompt=system_prompt
        )

    # single_agents/simple_agent/agent.py
    def interact(self, user_input: str) -> str:
        messages = self._format_messages(user_input)
        metadata = {
            "agent_name": self.name,
            "agent_id": self.id,
            "system_prompt": self.system_prompt
        }
        
        try:
            # Now correctly using messages parameter
            response = self.llm.query(
                messages=messages,
                metadata=metadata
            )
            return response
        except Exception as e:
            return f"Error generating response: {str(e)}"

if __name__ == "__main__":
    # Test with custom system prompt
    agent = SimpleAgent(
        system_prompt="You are a joke expert. Always respond with funny jokes."
    )
    print(agent.interact("Tell me a programming joke."))