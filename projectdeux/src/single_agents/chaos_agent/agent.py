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

    def interact(self, user_input: str) -> str:
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]
        response = litellm.completion(
            model=self.model,
            messages=messages,
            api_key=self.api_key,
            logger_fn=my_custom_logging_fn,
            metadata={"agent_name": self.name, "agent_id": self.id}
        )
        return response["choices"][0]["message"]["content"]

if __name__ == "__main__":
    agent = ChaosAgent()
    print("ChaosAgent test response:", agent.interact("What is the meaning of unpredictability?"))
