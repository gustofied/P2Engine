from orchestrator.schemas.schemas import AskSchema, ReplySchema


class RuleBasedAgent:
    def __init__(self, rules: dict[str, str]):
        self.rules = rules

    async def run(self, input: AskSchema) -> ReplySchema:
        if input.history:
            question = input.history[-1].get("content", "").lower()
            response = self.rules.get(question, "I don’t have a rule for that.")
        else:
            response = "No question provided."
        return ReplySchema(message=response)
