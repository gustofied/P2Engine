# Infrastructure Module

Core infrastructure components providing foundational services for p2engine.

## Overview

The infra module provides:

- Configuration management
- Logging and metrics
- Redis integration
- LLM client abstraction
- Artifact storage system
- Evaluation framework
- Session management
- Utility functions

## Architecture

```
infra/
├── artifacts/            # Event/artifact storage system
│   ├── bus.py           # Central event bus
│   ├── schema.py        # Type definitions
│   ├── export.py        # Export utilities
│   ├── drivers/         # Storage backends
│   │   ├── base.py     # Abstract driver
│   │   ├── fs_driver.py # Filesystem storage
│   │   └── s3_driver.py # S3 storage (stub)
│   └── lua/
│       └── next_idx.lua # Atomic operations
├── clients/              # External service clients
│   ├── llm_client.py    # LLM API wrapper
│   └── redis_client.py  # Redis connection
├── evals/                # Evaluation framework
│   ├── registry.py      # Evaluator registry
│   ├── llm_eval.py      # LLM-based evaluation
│   ├── gpt4_judge.py    # GPT-4 judge implementation
│   ├── metrics.py       # Metric calculations
│   ├── aggregate.py     # Score aggregation
│   ├── batcher.py       # Batch processing
│   ├── loader.py        # Plugin loader
│   ├── rubric_library.py # Evaluation rubrics
│   ├── templates/       # Eval prompts
│   └── rubrics/         # Rubric definitions
├── logging/              # Structured logging
│   ├── logging_config.py # Logger setup
│   ├── metrics.py       # Metrics emission
│   ├── effect_log.py    # Effect tracking
│   └── interaction_log.py # Interaction tracking
├── utils/                # Utility functions
│   ├── llm_helpers.py   # LLM utilities
│   ├── override_helpers.py # Override management
│   ├── redis_helpers.py # Redis utilities
│   ├── redis_keys.py    # Key generation
│   └── session_helpers.py # Session utilities
├── config.py            # Configuration models
├── config_loader.py     # Configuration loading
├── session.py           # Session management
├── session_driver.py    # Session orchestration
├── bootstrap.py         # System initialization
├── async_utils.py       # Async helpers
└── side_effect_executor.py # Effect execution
```

## Core Components

### Configuration System

#### Configuration Models (`config.py`)

```python
class AppSettings(BaseSettings):
    redis: RedisSettings
    llm: LLMSettings
    logging: LoggingSettings
    mode: str = "production"
    agent: AgentSettings
    ledger: LedgerSettings
```

#### Configuration Loading (`config_loader.py`)

```python
# Load settings (cached)
settings = settings()  # Returns AppSettings

# Load agent configurations
agents = agents()  # Returns List[AgentConfig]

# Configuration precedence:
# 1. Environment variables
# 2. config/config.json
# 3. Default values
```

#### Example Configuration

```json
{
  "redis": {
    "host": "localhost",
    "port": 6379,
    "db": 0
  },
  "llm": {
    "api_base": "https://api.openai.com/v1",
    "models": {
      "default_model": "openai/gpt-4o",
      "supported_models": {
        "openai/gpt-4o": { "provider": "openai" }
      }
    }
  },
  "ledger": {
    "enabled": true,
    "json_api_url": "http://localhost:7575",
    "party_id": "p2engine::default"
  }
}
```

### Artifact Bus

The artifact bus is a central event store for all system events.

#### Core Concepts

```python
from infra.artifacts.bus import get_bus
from infra.artifacts.schema import ArtifactHeader

# Publish an artifact
header: ArtifactHeader = {
    "ref": generate_ref(),  # Unique ID
    "session_id": conversation_id,
    "agent_id": agent_id,
    "branch_id": branch_id,
    "episode_id": episode_id,
    "type": "tool_result",
    "mime": "application/json",
    "ts": current_timestamp(),
    "meta": {"custom": "data"}
}
bus.publish(header, payload)

# Search artifacts
results = bus.search(
    session_id,
    tag="evaluation",
    since="2024-01-01T00:00:00Z",
    limit=50
)

# Get specific artifact
header, payload = bus.get(ref)
```

#### Storage Architecture

```
Redis (Metadata):
- artifacts:{session}:index     # Lean headers
- artifacts:{session}:headers   # Full headers
- artifacts:{session}:timeline  # Temporal index
- artifacts:{session}:branch:{branch} # Branch index
- stream:artifacts             # Real-time stream

Filesystem/S3 (Payloads):
- artifacts/{session}/payloads/{ref}.{ext}
- Compressed if > 2KB
- Journal backup in NDJSON
```

#### Artifact Types

- **state**: Conversation states
- **tool_call**: Tool invocations
- **tool_result**: Tool outputs
- **evaluation**: Quality assessments
- **metrics**: Performance data
- **ledger_event**: Financial transactions

### LLM Client

Abstraction over LLM APIs using litellm:

```python
from infra.clients.llm_client import LLMClient

client = LLMClient(
    api_key=api_key,
    api_base="https://api.openai.com/v1",
    model="openai/gpt-4o"
)

# Synchronous query
response = client.query(
    messages=[{"role": "user", "content": "Hello"}],
    tools=[tool_schema],
    temperature=0.7
)

# Async query with retry
response = await client.aquery(
    messages=messages,
    conversation_id=conv_id,  # For metrics
    agent_id=agent_id,
    branch_id=branch_id
)
```

Features:

- Automatic retries with exponential backoff
- Token usage tracking
- Cost calculation
- Metrics publishing
- Multiple provider support via litellm

### Session Management

Thread-safe session handling:

```python
from infra.session import get_session, Session

# Get or create session (thread-local)
session = get_session(conversation_id, redis_client)

# Register agents
session.register_agent("agent_alpha")

# Get conversation stack
stack = session.stack_for("agent_alpha")

# Session properties
tick = session.tick  # Current tick number
session.save()      # Persist state
```

### Evaluation Framework

#### Evaluator Registry

```python
from infra.evals import evaluator, registry

@evaluator(id="my_evaluator", version="1.0")
def my_evaluator(traj: List[dict], rubric: str, **kwargs) -> dict:
    # Evaluation logic
    return {
        "score": 0.85,
        "metrics": {"clarity": 0.9, "accuracy": 0.8},
        "comment": "Good response"
    }

# Get evaluator
eval_fn = registry.get("my_evaluator")
result = eval_fn(trajectory, rubric="Be strict")
```

#### GPT-4 Judge

Built-in LLM-based evaluator:

```python
# Automatic evaluation after agent completion
bus.create_evaluation_for(
    target_ref,  # Artifact to evaluate
    evaluator_id="gpt4_judge",
    payload={
        "traj": conversation_history,
        "rubric": "Rate helpfulness 0-1"
    }
)
```

#### Evaluation Rubrics

```jinja2
# rubrics/joke_quality.jinja
You are a comedy critic.
Score 1.0 if:
- Genuinely funny
- Original content
- Good timing

Score 0.0 if:
- Not a joke
- Offensive content
```

### Logging System

Structured JSON logging with Rich console output:

```python
from infra.logging.logging_config import logger

# Structured logging
logger.info({
    "message": "Tool executed",
    "tool_name": "get_weather",
    "conversation_id": conv_id,
    "latency_ms": 250
})

# Automatic log rotation
# Files: logs/main.log, logs/litellm_debug.log

# Metrics emission
from infra.logging.metrics import metrics
metrics.emit("tool_latency", 250, tags={"tool": "weather"})
```

### Utility Functions

#### LLM Helpers

```python
from infra.utils.llm_helpers import estimate_tokens, summarise

tokens = estimate_tokens("Long text...")  # Rough estimate
summary = summarise(text, limit_chars=750)  # Smart truncation
```

#### Redis Helpers

```python
from infra.utils.redis_helpers import serialise_for_redis
from infra.utils.redis_keys import event_sequence_key

# Safe serialization
data = serialise_for_redis({"key": complex_object})

# Consistent key generation
key = event_sequence_key(conversation_id, agent_id)
# Returns: "conversation:{conv_id}:{agent_id}:event_sequence"
```

#### Override Helpers

```python
from infra.utils.override_helpers import write_override

# Set agent overrides (with lock support)
success = write_override(redis, agent_id, conv_id, {
    "model": "gpt-4o",
    "temperature": 0.3,
    "lock": True  # Prevent further changes
})
```

### Bootstrap Process

System initialization (`bootstrap.py`):

```python
def run_once_global_init():
    # 1. Load evaluators
    # 2. Import tools
    # 3. Initialize services
    # 4. Start event loop
    # 5. Configure artifact bus
```

Special handling for Celery workers:

- Minimal initialization
- Separate Redis connections
- Worker-specific logging

### Async Utilities

Background event loop management:

```python
from infra.async_utils import run_async, set_event_loop

# Run coroutine from sync code
result = run_async(async_function())

# Fire and forget
run_async_fire_and_forget(async_task())

# Event loop is created automatically if needed
```

## Best Practices

### Configuration

1. Use environment variables for secrets
2. Keep config files in version control (except secrets)
3. Use type-safe configuration models
4. Cache configuration lookups

### Artifact Bus

1. Always include required header fields
2. Use appropriate MIME types
3. Implement retention policies
4. Monitor storage usage

### Sessions

1. Use get_session() for thread safety
2. Register agents before use
3. Save sessions after modifications
4. Clean up finished sessions

### Logging

1. Use structured logging (dicts)
2. Include correlation IDs
3. Set appropriate log levels
4. Monitor log file sizes

### Evaluation

1. Version your evaluators
2. Use consistent rubrics
3. Cache evaluation results
4. Aggregate scores meaningfully

## Performance Considerations

### Redis Optimization

- Use pipelining for bulk operations
- Set appropriate TTLs
- Monitor memory usage
- Use Lua scripts for atomicity

### Artifact Storage

- Payloads compressed if > 2KB
- Filesystem journal for backup
- Automatic pruning of old artifacts
- Consider S3 for production

### Session Management

- Thread-local session caching
- Lazy initialization
- Automatic cleanup
- Branch pruning

## Monitoring

### Key Metrics

- Redis connection pool usage
- Artifact storage size
- LLM API latency
- Evaluation processing time
- Session active count

### Health Checks

```python
# Redis connectivity
redis_client.ping()

# LLM API availability
await llm_client.aquery(test_message)

# Artifact bus operations
bus.get_bus().redis.ping()
```

## Extension Points

### Custom Storage Driver

```python
from infra.artifacts.drivers.base import BaseStorageDriver

class MyStorageDriver(BaseStorageDriver):
    def write_payload(self, session_id, ref, payload, mime, header):
        # Custom implementation
        pass

    def read_payload(self, session_id, ref, mime):
        # Custom implementation
        pass
```

### Custom Evaluator

```python
@evaluator(id="domain_expert", version="1.0")
def domain_expert_eval(traj, **kwargs):
    # Domain-specific evaluation
    return {"score": score, "metrics": {...}}
```

### Custom Metrics Backend

```python
class CustomMetrics:
    def emit(self, name, value, tags=None):
        # Send to monitoring system
        pass

metrics._backend = CustomMetrics()
```
