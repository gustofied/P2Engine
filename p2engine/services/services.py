from __future__ import annotations
import os
import threading
import time
from pathlib import Path
from typing import Optional

import redis
from jinja2 import FileSystemLoader
from jinja2.sandbox import SandboxedEnvironment

from agents.agents import AgentFactory
from infra.artifacts.bus import ArtifactBus
from infra.artifacts.drivers.fs_driver import FSStorageDriver
from infra.artifacts.drivers.s3_driver import S3StorageDriver
from infra.clients.llm_client import LLMClient
from infra.config import BASE_DIR, AppSettings
from infra.config_loader import settings
from infra.logging.logging_config import litellm_logging_fn, logger
from infra.redis_repository import RedisRepository
from orchestrator.registries import AgentRegistry, ToolRegistry
from orchestrator.registries import tool_registry as global_tool_registry
from orchestrator.renderer.template_manager import TemplateManager
from runtime.policies.dedup import (
    BaseDedupPolicy,
    NoDedupPolicy,
    PenaltyDedupPolicy,
    StrictDedupPolicy,
)
from services.ledger_service import CantonLedgerService
from tools import load_tools

# Load all tools at module import
load_tools()


def _await_redis_ready(rds: redis.Redis, *, timeout: float = 5.0) -> None:
    """Wait for Redis to be ready"""
    deadline = time.time() + timeout
    while True:
        try:
            if rds.ping():
                return
        except redis.exceptions.ConnectionError:
            pass
        if time.time() >= deadline:
            raise ConnectionError("Redis not responding on host/port configured in settings")
        time.sleep(0.1)


def _make_dedup_policy(name: str, rds: redis.Redis, tools: ToolRegistry) -> BaseDedupPolicy:
    """Create deduplication policy instance"""
    name = name.lower()
    policy_map = {
        "none": NoDedupPolicy,
        "penalty": PenaltyDedupPolicy,
        "strict": StrictDedupPolicy,
    }
    if name not in policy_map:
        raise ValueError(f"Unknown DEDUP_POLICY: {name}")

    cls = policy_map[name]
    return cls() if cls is NoDedupPolicy else cls(rds, tools)


class ServiceContainer:
    """Central service container for dependency injection"""

    def __init__(
        self,
        llm_client: Optional[LLMClient] = None,
        redis_client: Optional[redis.Redis] = None,
        template_manager: Optional[TemplateManager] = None,
        agent_registry: Optional[AgentRegistry] = None,
        tool_registry: Optional[ToolRegistry] = None,
    ) -> None:
        self._settings: AppSettings = settings()

        # Initialize LLM client
        self._llm_client = llm_client or LLMClient(
            api_key=self._settings.llm.api_key,
            api_base=self._settings.llm.api_base,
            model=self._settings.llm.models.default_model,
            logger_fn=litellm_logging_fn,
        )

        # Initialize Redis
        self._redis_local = threading.local()

        def _new_redis() -> redis.Redis:
            rds = redis.Redis(
                host=self._settings.redis.host,
                port=self._settings.redis.port,
                db=self._settings.redis.db,
                decode_responses=True,
            )
            _await_redis_ready(rds)
            return rds

        self._redis_local.client = redis_client or _new_redis()
        self._redis_client = self._redis_local.client

        # Initialize repository
        self._repository = RedisRepository(self.get_redis_client())

        # Initialize template manager
        templates_dir = os.path.join(BASE_DIR, "agents", "templates")
        loader = FileSystemLoader(templates_dir)
        self._template_manager = template_manager or TemplateManager(SandboxedEnvironment(loader=loader))

        # Initialize tool registry
        self._tool_registry = tool_registry or global_tool_registry
        logger.info(
            "ServiceContainer initialised with tools: %s",
            list(self._tool_registry._tools.keys()),
        )

        # Initialize agent factory and registry
        self._agent_factory = AgentFactory(
            llm_client=self._llm_client,
            tool_registry=self._tool_registry,
            template_manager=self._template_manager,
        )

        self._agent_registry = agent_registry or AgentRegistry(
            repository=self._repository,
            agent_factory=self._agent_factory,
        )

        # Initialize artifact storage
        artifact_driver = os.getenv("ARTIFACT_DRIVER", "fs")
        if artifact_driver == "fs":
            driver = FSStorageDriver(base_dir=Path(os.getenv("LOG_DIR", BASE_DIR)))
        elif artifact_driver == "s3":
            bucket = os.getenv("S3_BUCKET")
            if not bucket:
                raise ValueError("S3_BUCKET environment variable is required for S3 driver")
            driver = S3StorageDriver(bucket=bucket)
        else:
            raise ValueError(f"Unknown ARTIFACT_DRIVER: {artifact_driver}")

        self._artifact_bus = ArtifactBus.get_instance(
            redis_client=self.get_redis_client(),
            driver=driver,
        )

        # Initialize dedup policy
        policy_name = os.getenv("DEDUP_POLICY", "none")
        self._dedup_policy = _make_dedup_policy(policy_name, self.get_redis_client(), self._tool_registry)

        # Initialize ledger service if enabled
        self._ledger_service = None
        if self._settings.ledger.enabled:
            try:
                from services.ledger_service import CantonLedgerService, LedgerConfig

                # Check if package ID is available
                package_id = os.getenv("DAML_PACKAGE_ID")
                if not package_id:
                    logger.warning("DAML_PACKAGE_ID not set - ledger service may not function correctly")

                ledger_config = LedgerConfig(
                    json_api_url=self._settings.ledger.json_api_url,
                    party_id=self._settings.ledger.party_id,
                    initial_balance=self._settings.ledger.initial_balance,
                    cache_ttl=self._settings.ledger.cache_ttl,
                    package_id=package_id,
                )
                self._ledger_service = CantonLedgerService(ledger_config)
                logger.info("Ledger service initialized with package ID: %s", package_id)
            except Exception as exc:
                logger.warning(f"Ledger service initialization failed: {exc}")
                self._ledger_service = None

        logger.info("ServiceContainer initialized")

    def get_redis_client(self) -> redis.Redis:
        """Get thread-local Redis client"""
        if not hasattr(self._redis_local, "client"):
            self._redis_local.client = self.new_redis_client()
        return self._redis_local.client

    def new_redis_client(self) -> redis.Redis:
        """Create new Redis client"""
        rds = redis.Redis(
            host=self._settings.redis.host,
            port=self._settings.redis.port,
            db=self._settings.redis.db,
            decode_responses=True,
        )
        _await_redis_ready(rds)
        return rds

    def get_llm_client(self) -> LLMClient:
        return self._llm_client

    def get_template_manager(self) -> TemplateManager:
        return self._template_manager

    def get_tool_registry(self) -> ToolRegistry:
        return self._tool_registry

    def get_agent_factory(self) -> AgentFactory:
        return self._agent_factory

    def get_agent_registry(self) -> AgentRegistry:
        return self._agent_registry

    def get_artifact_bus(self) -> ArtifactBus:
        return self._artifact_bus

    def get_dedup_policy(self) -> BaseDedupPolicy:
        return self._dedup_policy

    def get_ledger_service(self) -> Optional["CantonLedgerService"]:
        """Get ledger service if available"""
        return self._ledger_service
