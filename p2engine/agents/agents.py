# TODO Check agents.py the factory/plugin against our IAgent?
from typing import List

from infra import config_loader as cfg
from infra.clients.redis_client import get_redis
from orchestrator.schemas.schemas import AgentConfig


class AgentFactory:
    def __init__(self, llm_client, tool_registry, template_manager, plugin_mgr=None):
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.template_manager = template_manager
        self.redis_client = get_redis()
        self.plugins = plugin_mgr or AgentPluginManager()

    def load_all(self) -> List[AgentConfig]:
        return cfg.agents()

    def create(self, cfg: AgentConfig):
        cls = self.plugins.get(cfg.type)
        if cfg.type == "llm":
            return cls(
                agent_id=cfg.id,
                model=cfg.llm_model,
                tool_names=cfg.tools,
                behavior_template=cfg.behavior_template,
                llm_client=self.llm_client,
                tool_registry=self.tool_registry,
                template_manager=self.template_manager,
                redis_client=self.redis_client,
                config=cfg,
            )
        if cfg.type == "rule_based":
            return cls(rules=cfg.rules)
        if cfg.type == "human_in_loop":
            return cls(callback_url=cfg.callback_url, agent_id=cfg.id)
        raise ValueError(f"Unknown agent type: {cfg.type}")


class AgentPluginManager:
    def __init__(self):
        from importlib.metadata import entry_points

        from infra.logging.logging_config import logger

        self._registry = {}
        for ep in entry_points(group="agents"):
            try:
                self._registry[ep.name] = ep.load()
            except ModuleNotFoundError as exc:
                logger.error(f"Failed to load plugin {ep.name}: {exc}")
        if not self._registry:
            logger.warning("No agent plugins found via entry-points; falling back to " "built-in agent classes.")
            from agents.impl.human_in_loop_agent import HumanInLoopAgent
            from agents.impl.llm_agent import LLMAgent
            from agents.impl.rule_agent import RuleBasedAgent

            self._registry.update(
                {
                    "llm": LLMAgent,
                    "rule_based": RuleBasedAgent,
                    "human_in_loop": HumanInLoopAgent,
                }
            )

    def get(self, agent_type: str):
        if agent_type not in self._registry:
            raise ValueError(f"No agent plugin for type “{agent_type}”")
        return self._registry[agent_type]
