from typing import Optional, List, Any
import litellm
from single_agents.base_agent import BaseAgent
from custom_logging.litellm_logger import my_custom_logging_fn

class ChaosAgent(BaseAgent):
    def __init__(
        self,
        name: str = "ChaosAgent",
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        tools: Optional[List[Any]] = None
    ):
        super().__init__(name=name, model=model, api_key=api_key, tools=tools)
        self.system_prompt = (
            "You are Chaos: unpredictable, creative, and cryptic. "
            "Respond in bizarre metaphors, whimsical riddles, and surreal imagery."
        )

    # single_agents/chaos_agent/agent.py
    def interact(self, user_input: str) -> str:
        messages = self._format_messages(user_input)  # Use inherited message formatting
        response = self.llm.query(  # Use LLMClient instead of direct litellm call
            messages=messages,
            metadata={"agent_name": self.name, "agent_id": self.id}
        )
        return response

if __name__ == "__main__":
    agent = ChaosAgent()
    print("ChaosAgent test response:", agent.interact("What is the meaning of unpredictability?"))
