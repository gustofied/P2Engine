# agents/impl/human_in_loop_agent.py
from infra.logging.logging_config import logger
from orchestrator.schemas.schemas import AskSchema, ReplySchema


class HumanInLoopAgent:
    def __init__(self, callback_url: str | None, agent_id: str):
        self.callback_url = callback_url
        self.agent_id = agent_id

    async def run(self, input: AskSchema) -> ReplySchema:
        response = "Waiting for human response..."
        if self.callback_url and input.history:
            latest_message = input.history[-1].get("content", "")
            logger.info(
                {
                    "message": f"Human intervention requested at {self.callback_url} for: {latest_message}",
                    "agent_id": self.agent_id,
                }
            )
        return ReplySchema(message=response)
