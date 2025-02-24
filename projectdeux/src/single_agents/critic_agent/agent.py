from typing import Optional, List, Any
from single_agents.base_agent import BaseAgent

class CriticAgent(BaseAgent):
    def __init__(
        self,
        name: str = "CriticAgent",
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        tools: Optional[List[Any]] = None
    ):
        super().__init__(name=name, model=model, api_key=api_key, tools=tools)
        self.critique_prompt = (
            "You are a critic analyzing the conversation. "
            "Based on the conversation so far, indicate if additional specialized agents are needed. "
            "If so, suggest the type or name of the new agent(s). If the problem is solved, simply say 'solved'."
        )

    # single_agents/critic_agent/agent.py
    def interact(self, conversation_history: str) -> str:
        prompt = f"{self.critique_prompt}\n\nConversation so far:\n{conversation_history}"
        messages = self._format_messages(prompt)  # Use BaseAgent's message formatting
        response = self.llm.query(
            messages=messages,  # Pass formatted messages
            metadata={"agent_name": self.name, "agent_id": self.id}
        )
        return response
