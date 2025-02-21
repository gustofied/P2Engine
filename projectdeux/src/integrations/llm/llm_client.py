import os
import litellm

class LLMClient:
    def __init__(self, model: str = "gpt-3.5-turbo", api_key: str = None, logger_fn=None):
        self.model = model
        # Load API key from the environment variable if not provided.
        self.api_key = api_key or os.getenv("OPENAI_APY_KEY")
        if not self.api_key:
            raise ValueError("API key must be provided either as an argument or via the OPENAI_APY_KEY environment variable.")
        self.logger_fn = logger_fn

    def query(self, prompt: str, metadata: dict = None) -> str:
        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            api_key=self.api_key,
            logger_fn=self.logger_fn,  # Use our custom logger.
            metadata=metadata         # Pass agent metadata (e.g., agent_id).
        )
        return response["choices"][0]["message"]["content"]
