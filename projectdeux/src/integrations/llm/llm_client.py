import os
import logging
import litellm
from typing import Optional, Dict
from custom_logging.litellm_logger import my_custom_logging_fn

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

class LLMClient:
    SUPPORTED_MODELS = {
        "gpt-3.5-turbo": {"provider": "openai"},
        "gpt-4": {"provider": "openai"},
        "text-davinci-003": {"provider": "openai"}
    }

    def __init__(
        self,
        model: str = "gpt-3.5-turbo",
        api_key: Optional[str] = None,
        logger_fn=None,
        debug: bool = False
    ) -> None:
        if model not in self.SUPPORTED_MODELS:
            raise ValueError(f"Model {model} is not supported.")

        self.model = model
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("API key is missing.")

        self.logger_fn = logger_fn if logger_fn is not None else my_custom_logging_fn
        self.debug = debug

        if self.debug:
            logger.setLevel(logging.DEBUG)

    def query(self, prompt: str, metadata: Optional[Dict] = None) -> str:
        metadata = metadata or {}
        if self.debug:
            metadata['debug'] = True

        response = litellm.completion(
            model=self.model,
            messages=[{"role": "user", "content": prompt}],
            api_key=self.api_key,
            logger_fn=self.logger_fn,
            metadata=metadata
        )

        return response["choices"][0]["message"]["content"]
