import os
import logging
import litellm
from typing import List, Optional, Dict
from custom_logging.litellm_logger import my_custom_logging_fn
from dotenv import load_dotenv

# Load environment variables from a .env file if present
load_dotenv()

logger = logging.getLogger(__name__)

class LLMClient:
    SUPPORTED_MODELS = {
        "openai/gpt-3.5-turbo": {"provider": "openai"},
        "openai/gpt-4": {"provider": "openai"},
        "gpt-3.5-turbo": {"provider": "openai"},
        "gpt-4": {"provider": "openai"},
        "github/gpt-4o": {"provider": "github"},
        # Support both model strings for Deepseek:
        "deepseek-chat": {"provider": "deepseek"},
        "deepseek/deepseek-chat": {"provider": "deepseek"},
    }

    def __init__(
        self,
        model: str = "deepseek-chat",
        api_key: Optional[str] = None,
        logger_fn=my_custom_logging_fn,
        debug: bool = False
    ) -> None:
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} is not supported.")
        self.model = model
        provider = self.SUPPORTED_MODELS[model]["provider"]
        # Use the appropriate environment variable based on provider
        if provider == "github":
            self.api_key = api_key or os.getenv("GITHUB_API_KEY")
        elif provider == "deepseek":
            self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key is missing.")
        self.logger_fn = logger_fn
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)

    def query(self, messages: List[Dict], metadata: Optional[Dict] = None) -> str:
        """Send a query to the LLM and return the response."""
        metadata = metadata or {}
        if self.debug:
            metadata['debug'] = True
        # Debug print to confirm logger_fn is set
        print(f"Calling litellm.completion with logger_fn: {self.logger_fn}")
        try:
            response = litellm.completion(
                model=self.model,
                messages=messages,
                api_key=self.api_key,
                logger_fn=self.logger_fn,
                metadata=metadata
            )
            return response["choices"][0]["message"]["content"]
        except Exception as e:
            logger.error(f"LLM query failed: {e}")
            raise e
