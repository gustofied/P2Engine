from typing import Protocol, TypeVar, runtime_checkable


@runtime_checkable
class _HasRedis(Protocol):
    def get_redis_client(self): ...


@runtime_checkable
class _HasAgentRegistry(Protocol):
    def get_agent_registry(self): ...


T = TypeVar("T")


def _as_container(obj: T):
    """
    If *obj* looks like an Engine (i.e. exposes a ``container`` attribute),
    unwrap it; otherwise return it unchanged.
    """
    return obj.container if hasattr(obj, "container") else obj


def get_redis(obj):
    """
    Always return a **redis.Redis** instance, regardless of what wrapper
    object the caller hands us.

    Accepts:
      • an Engine              → unwrap ``.container`` then ``.get_redis_client()``
      • a ServiceContainer     → call ``.get_redis_client()``
      • a bare redis.Redis     → return as-is
    """
    c = _as_container(obj)
    if hasattr(c, "get_redis_client"):
        return c.get_redis_client()
    return c  


def get_agent_registry(obj):
    """
    Same idea as *get_redis* but for the **AgentRegistry**.

    Accepts:
      • an Engine              → unwrap then ``.get_agent_registry()``
      • a ServiceContainer     → call ``.get_agent_registry()``
      • a bare AgentRegistry   → return as-is
    """
    c = _as_container(obj)
    if hasattr(c, "get_agent_registry"):
        return c.get_agent_registry()
    return c 
