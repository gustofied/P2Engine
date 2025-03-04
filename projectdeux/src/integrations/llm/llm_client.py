import os
import logging
import litellm
from typing import List, Optional, Dict
from src.custom_logging.litellm_logger import my_custom_logging_fn
from dotenv import load_dotenv
import time

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
        "deepseek-chat": {"provider": "deepseek"},
        "deepseek/deepseek-chat": {"provider": "deepseek"},
        "together_ai/deepseek-ai/DeepSeek-R1-Distill-Qwen-1.5B": {"provider": "together_ai"},
        "openrouter/google/gemini-2.0-flash-001": {"provider": "openrouter"},
        "gemini-2.0-flash-001": {"provider": "openrouter"},
    }

    def __init__(
        self,
        model: str = "openrouter/google/gemini-2.0-flash-001",
        api_key: Optional[str] = None,
        logger_fn=my_custom_logging_fn,
        debug: bool = False
    ) -> None:
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} is not supported.")
        self.model = model
        provider = self.SUPPORTED_MODELS[model]["provider"]
        # Set the API key based on the provider
        if provider == "github":
            self.api_key = api_key or os.getenv("GITHUB_API_KEY")
        elif provider == "deepseek":
            self.api_key = api_key or os.getenv("DEEPSEEK_API_KEY")
        elif provider == "together_ai":
            self.api_key = api_key or os.getenv("TOGETHER_AI_API_KEY")
        elif provider == "openrouter":
            self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
            print(f"OpenRouter API Key: {self.api_key}")  # Debug print
        else:
            self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError(f"API key for {provider} is missing.")
        self.logger_fn = logger_fn
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)

    def query(self, messages: List[Dict], metadata: Optional[Dict] = None) -> str:
        """Send a query to the LLM and return the response with retry logic."""
        metadata = metadata or {}
        if self.debug:
            metadata['debug'] = True
        print(f"Calling litellm.completion with logger_fn: {self.logger_fn}")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                # Add api_base for OpenRouter if provider is "openrouter"
                extra_kwargs = {}
                if self.SUPPORTED_MODELS[self.model]["provider"] == "openrouter":
                    extra_kwargs["api_base"] = "https://openrouter.ai/api/v1"

                response = litellm.completion(
                    model=self.model,
                    messages=messages,
                    api_key=self.api_key,
                    logger_fn=self.logger_fn,
                    metadata=metadata,
                    **extra_kwargs
                )
                return response["choices"][0]["message"]["content"]
            except Exception as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in 2 seconds...")
                    time.sleep(2)
                else:
                    logger.error(f"LLM query failed after {max_retries} attempts: {e}")
                    raise e