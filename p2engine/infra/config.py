import json
import logging
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic_settings import BaseSettings

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


class RedisSettings(BaseSettings):
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    db: int = Field(default=0, env="REDIS_DB")
    model_config = ConfigDict(extra="forbid")


class ModelsConfig(BaseModel):
    supported_models: Dict[str, Dict[str, Any]]
    default_model: str
    model_config = ConfigDict(extra="forbid")


class LLMSettings(BaseSettings):
    api_key: str = Field(..., env="OPENAI_API_KEY")
    api_base: str = Field(default="https://api.openai.com/v1", env="OPENAI_API_BASE")
    models: ModelsConfig
    model_config = ConfigDict(extra="forbid")


class LoggingSettings(BaseSettings):
    log_dir: str = Field(default="logs", env="LOG_DIR")
    log_file: str = Field(default="main.log", env="LOG_FILE")
    model_config = ConfigDict(extra="forbid")


class AgentSettings(BaseModel):
    technical_failure_message: str = Field(default="Sorry, I'm experiencing technical difficulties. Please try again later.")
    model_config = ConfigDict(extra="forbid")


class LedgerSettings(BaseSettings):
    enabled: bool = Field(default=True, env="LEDGER_ENABLED")
    json_api_url: str = Field(default="http://localhost:7575", env="LEDGER_API_URL")
    party_id: str = Field(default="p2engine::default", env="LEDGER_PARTY_ID")
    initial_balance: float = Field(default=100.0, env="LEDGER_INITIAL_BALANCE")
    cache_ttl: int = Field(default=60, env="LEDGER_CACHE_TTL")
    model_config = ConfigDict(extra="forbid")


class AppSettings(BaseSettings):
    redis: RedisSettings = RedisSettings()
    llm: LLMSettings
    logging: LoggingSettings = LoggingSettings()
    mode: str = Field(default="production", description="Mode: production or development")
    agent: AgentSettings = AgentSettings()
    ledger: LedgerSettings = LedgerSettings()
    model_config = ConfigDict(extra="forbid", env_nested_delimiter="__")


def load_settings() -> AppSettings:
    """Load settings from config file"""
    default_config_path = Path(BASE_DIR) / "config" / "config.json"
    config_path = Path(os.getenv("P2ENGINE_CONFIG_PATH", default_config_path))

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found at {config_path}")

    with config_path.open() as f:
        config_data = json.load(f)

    # Ensure LLM API key is set
    from os import getenv

    config_data.setdefault("llm", {})
    llm_cfg = config_data["llm"]
    if not llm_cfg.get("api_key"):
        llm_cfg["api_key"] = getenv("OPENAI_API_KEY")

    try:
        settings = AppSettings(**config_data)
    except ValidationError as e:
        logger.error(f"Invalid configuration in {config_path}: {e}")
        raise

    return settings
