import json
import threading
from typing import Dict, List, Optional

from pydantic import TypeAdapter

from agents.interfaces import IAgent, IAgentRegistry, IRepository, ITool
from infra.config_loader import settings
from infra.logging.logging_config import logger
from orchestrator.schemas.schemas import AgentConfig, LLMAgentConfig

# ---------------------------------------------------------------------------
# Tool registry
# ---------------------------------------------------------------------------


class ToolRegistry:
    """Thread-safe registry for tool implementations."""

    def __init__(self) -> None:
        self._tools: Dict[str, ITool] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register(self, tool: ITool) -> bool:
        """Register *tool* by its unique ``name``.

        Returns ``True`` if the tool was added – ``False`` when the name was
        already present."""
        with self._lock:
            if tool.name in self._tools:
                return False
            self._tools[tool.name] = tool
            return True

    def get_tools(self) -> List[ITool]:
        with self._lock:
            return list(self._tools.values())

    def get_tool_by_name(self, name: str) -> Optional[ITool]:
        with self._lock:
            return self._tools.get(name)

    def list_tools(self) -> Dict[str, str]:
        with self._lock:
            return {tool.name: tool.description for tool in self._tools.values()}


tool_registry = ToolRegistry()

# ---------------------------------------------------------------------------
# Agent registry
# ---------------------------------------------------------------------------


class AgentRegistry(IAgentRegistry):
    """Holds *live* agent instances and knows how to lazily materialise new
    ones.

    Resolution order in :meth:`get_agent`:

    1. **Memory** – already instantiated within this worker.
    2. **Redis** – persisted by a sibling worker in a previous run.
    3. **YAML**  – static definition in ``config/agents.yml``.
    4. **Template (auto-create)** – synthesize a generic LLM agent with the
       default model and the full tool-box when nothing else matches.

    The auto-create step makes delegation to arbitrary ``agent_id`` values work
    out-of-the-box in early-stage projects.
    """

    def __init__(self, repository: IRepository, agent_factory) -> None:
        self.repository = repository
        self.agent_factory = agent_factory

        self._agents: Dict[str, IAgent] = {}
        self._lock = threading.Lock()

    # ------------------------------------------------------------------
    # IAgentRegistry implementation
    # ------------------------------------------------------------------

    def register(self, agent: IAgent, config: AgentConfig) -> None:
        with self._lock:
            agent_id = config.id

            # avoid duplicate work – check Redis *and* local cache
            if self.repository.redis.sismember("active_agents", agent_id):
                logger.info(
                    {
                        "message": f"Agent '{agent_id}' already registered in Redis. Skipping.",
                        "agent_id": agent_id,
                    }
                )
                return
            if agent_id in self._agents:
                logger.info(
                    {
                        "message": f"Agent '{agent_id}' already in local registry. Skipping.",
                        "agent_id": agent_id,
                    }
                )
                return

            # persist + mark active
            self._agents[agent_id] = agent
            self.repository.set(f"agent:{agent_id}:config", json.dumps(config.model_dump()))
            self.repository.redis.sadd("active_agents", agent_id)

            logger.info(
                {
                    "message": "Agent registered with config",
                    "agent_id": agent_id,
                    "type": config.type,
                }
            )

    def unregister(self, agent_id: str) -> None:
        with self._lock:
            if agent_id in self._agents:
                del self._agents[agent_id]
                self.repository.delete(f"agent:{agent_id}:config")
                for key in self.repository.keys(f"fsm:{agent_id}:*"):
                    self.repository.delete(key)
                self.repository.redis.srem("active_agents", agent_id)
                logger.info({"message": "Agent unregistered", "agent_id": agent_id})
            else:
                logger.warning({"message": "Agent not found", "agent_id": agent_id})

    # ------------------------------------------------------------------
    # Core lookup logic
    # ------------------------------------------------------------------

    def get_agent(self, agent_id: str) -> Optional[IAgent]:
        """Return a *live* agent instance.

        Resolution order:

        1. In-memory
        2. Persisted in Redis
        3. Defined in ``config/agents.yml``
        4. **Auto-create** from a minimal template
        """
        with self._lock:
            # 1) already instantiated in this process
            if agent_id in self._agents:
                return self._agents[agent_id]

            # 2) persisted by a previous run / another worker
            config_str = self.repository.get(f"agent:{agent_id}:config")
            if config_str:
                try:
                    config_dict = json.loads(config_str)
                    config = TypeAdapter(AgentConfig).validate_python(config_dict)
                except Exception as exc:  # pragma: no cover – should never happen
                    logger.error(
                        {
                            "message": "Failed to parse persisted agent config",
                            "agent_id": agent_id,
                            "error": str(exc),
                        }
                    )
                    return None

                agent = self.agent_factory.create(config)
                self._agents[agent_id] = agent
                self.repository.redis.sadd("active_agents", agent_id)
                logger.info(
                    {
                        "message": "Agent recreated from repository",
                        "agent_id": agent_id,
                        "type": config.type,
                    }
                )
                return agent

            # 3) try the static YAML
            from infra.config_loader import agents as load_cfgs  # late import to avoid cycles

            cfg_map = {cfg.id: cfg for cfg in load_cfgs()}
            cfg = cfg_map.get(agent_id)
            if cfg is not None:
                agent = self.agent_factory.create(cfg)
                self.register(agent, cfg)
                logger.info(
                    {
                        "message": "Agent lazily materialised from YAML",
                        "agent_id": agent_id,
                        "type": cfg.type,
                    }
                )
                return agent

            # 4) -----------------------------------------------------------------
            #    AUTO-CREATE a generic LLM agent (default model, full tool-box)
            # -----------------------------------------------------------------
            default_model = settings().llm.models.default_model
            all_tools = list(self.agent_factory.tool_registry.list_tools().keys())

            cfg = LLMAgentConfig(
                type="llm",
                id=agent_id,
                llm_model=default_model,
                tools=all_tools,
            )

            agent = self.agent_factory.create(cfg)

            # persist & mark active so every worker sees it next time
            self._agents[agent_id] = agent
            self.repository.set(f"agent:{agent_id}:config", json.dumps(cfg.model_dump()))
            self.repository.redis.sadd("active_agents", agent_id)

            logger.info(
                {
                    "message": "Agent auto-created from template",
                    "agent_id": agent_id,
                    "tools": all_tools,
                }
            )
            return agent

    # ------------------------------------------------------------------

    def list_agents(self) -> Dict[str, str]:
        with self._lock:
            return {aid: self._agents[aid].__class__.__name__ for aid in self._agents}
