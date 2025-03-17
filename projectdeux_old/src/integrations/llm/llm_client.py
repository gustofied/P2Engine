import os
import json
import logging
import litellm
from typing import List, Optional, Dict
from src.custom_logging.central_logger import central_logger  # Updated import
from dotenv import load_dotenv
import time

# Load environment variables from a .env file if present
load_dotenv()

logger = logging.getLogger(__name__)

class LLMClient:
    def __init__(
        self,
        model: Optional[str] = None,
        api_key: Optional[str] = None,
        logger_fn=central_logger.log_litellm_event,  # Use CentralLogger's method
        debug: bool = False,
        config_path: Optional[str] = None,
        run_id: Optional[str] = None  # New parameter for run_id
    ) -> None:
        # Use provided run_id or fallback to CentralLogger's run_id
        self.run_id = run_id or central_logger.run_id
        
        # Determine config file path: provided path, env variable, or default
        config_path = config_path or os.getenv("MODELS_CONFIG_PATH", os.path.join(os.path.dirname(__file__), "models_config.json"))
        
        # Load configuration from the JSON file
        try:
            with open(config_path, "r") as f:
                config = json.load(f)
            self.supported_models = config["supported_models"]
            default_model = config["default_model"]
        except Exception as e:
            logger.error(f"Failed to load config from {config_path}: {e}")
            raise ValueError(f"Configuration file {config_path} not found or invalid.")
        
        # Set the model: use provided model or fall back to default from config
        self.model = model or default_model
        if self.model not in self.supported_models:
            raise ValueError(f"Model {self.model} is not supported.")
        
        # Determine the provider for the selected model
        provider = self.supported_models[self.model]["provider"]
        
        # Set the API key based on the provider
        api_key_env_var = f"{provider.upper()}_API_KEY"
        self.api_key = api_key or os.getenv(api_key_env_var)
        if not self.api_key:
            raise ValueError(f"API key for {provider} is missing. Set {api_key_env_var} environment variable.")
        
        self.logger_fn = logger_fn
        self.debug = debug
        if self.debug:
            logger.setLevel(logging.DEBUG)

    def query(self, messages: List[Dict], metadata: Optional[Dict] = None) -> str:
        """Send a query to the LLM and return the response with retry logic."""
        metadata = metadata or {}
        metadata['run_id'] = self.run_id  # Add run_id to metadata for tracing
        if self.debug:
            metadata['debug'] = True
        print(f"Calling litellm.completion with logger_fn: {self.logger_fn}")
        max_retries = 3
        for attempt in range(max_retries):
            try:
                extra_kwargs = {}
                if self.supported_models[self.model]["provider"] == "openrouter":
                    extra_kwargs["api_base"] = "https://openrouter.ai/api/v1"
                response = litellm.completion(
                    model=self.model,
                    messages=messages,
                    api_key=self.api_key,
                    logger_fn=self.logger_fn,  # Pass CentralLogger's log_litellm_event
                    metadata=metadata,
                    **extra_kwargs
                )
                return response["choices"][0]["message"]["content"]
            except Exception as e:
                error_context = {"attempt": attempt + 1, "model": self.model, "run_id": self.run_id}
                if attempt < max_retries - 1:
                    logger.warning(f"Attempt {attempt + 1} failed: {e}. Retrying in 2 seconds...", extra=error_context)
                    time.sleep(2)
                else:
                    logger.error(f"LLM query failed after {max_retries} attempts: {e}", extra=error_context)
                    central_logger.log_error("LLMClient", e, self.run_id, context=error_context)
                    raise e