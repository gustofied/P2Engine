Yep—exactly. You should **instrument from inside the modules** at the key “edges” where useful things happen. That’s how you’ll power timelines, graphs, and debugging later.

Here’s the skinny:

- **Where to log (high signal):**

  - `AgentFactory.create` → agent spawned (id, type, model, tools).
  - `IAgent.run` (each impl) → run started/ended (duration, outcome).
  - `LLMAgent` right before/after `llm_client.aquery` → LLMRequest/LLMResponse (model, tokens, latency).
  - `FunctionTool.execute` → ToolInvoked/ToolCompleted (tool name, cache hit/miss, duration).
  - `delegate` tool → DelegationRequested (parent→child).
  - `HumanInLoopAgent` → HumanInterventionRequested (callback_url present).
  - Episode/branch changes → EpisodeStarted / BranchSelected.

- **Always include correlation fields** so you can stitch events together:
  `conversation_id, agent_id, episode_id, branch_id, event_type, ts, trace_id/span_id`.

- **Keep it structured** (JSON), minimal, and privacy-safe (avoid raw message content; log lengths/hashes instead).

Tiny drop-in helper you can reuse:

```python
# infra/obs/events.py
import time, uuid, logging
log = logging.getLogger("obs")

def emit(event_type: str, **fields):
    log.info({"event_type": event_type, **fields})

class span:
    def __init__(self, event_type: str, **ctx):
        self.event_type, self.ctx = event_type, ctx
    def __enter__(self):
        self.ctx["span_id"] = uuid.uuid4().hex
        self.t0 = time.perf_counter()
        emit(self.event_type + "_started", **self.ctx)
        return self.ctx
    def __exit__(self, exc_type, *_):
        dur = (time.perf_counter() - self.t0) * 1000
        status = "error" if exc_type else "ok"
        emit(self.event_type + "_ended", duration_ms=round(dur, 2), status=status, **self.ctx)
```

Use it in your modules:

```python
# LLMAgent.run
from infra.obs.events import span, emit
with span("agent_run", conversation_id=input.conversation_id, agent_id=self.agent_id, branch_id=branch_id):
    emit("llm_request", model=base_params["model"])
    resp = await self.llm_client.aquery(... )
    emit("llm_response", has_tool_calls=bool(resp.choices[0].message.tool_calls))
```

```python
# FunctionTool.execute
from infra.obs.events import span, emit
with span("tool_execute", tool=self.name, conversation_id=context_params.get("conversation_id","NA")):
    emit("tool_cache_check", cache_enabled=bool(self.cache_ttl))
    ...
```

This gives you:

- clean **start/end** markers with durations
- consistent event shapes
- easy piping to your artifact bus / OpenTelemetry / logs → dashboards

So yes: log **inside** the agents/tools at those key points. Keep the import-time autoloader quiet; keep the runtime hot paths well-instrumented.
