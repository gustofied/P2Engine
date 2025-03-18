import json
import os
from dotenv import load_dotenv
import litellm

load_dotenv()

class LLMClient:
    def __init__(self, model=None, config_path=None):
        config_path = config_path or os.path.join(os.path.dirname(__file__), "../../models_config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        self.supported_models = config["supported_models"]
        self.default_model = config["default_model"]
        
        self.model = model or self.default_model
        if self.model not in self.supported_models:
            raise ValueError(f"Model {self.model} not supported.")
        
        self.provider = self.supported_models[self.model]["provider"]
        if self.provider == "openrouter":
            self.api_key = os.getenv("OPENROUTER_API_KEY")
            self.api_base = "https://openrouter.ai/api/v1"
        else:
            raise ValueError(f"Provider {self.provider} not supported.")
        
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY is missing.")

    def query(self, messages):
        response = litellm.completion(
            model=self.model,
            messages=messages,
            api_key=self.api_key,
            api_base=self.api_base
        )
        return response["choices"][0]["message"]["content"]