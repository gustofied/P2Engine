# Runtime Module

The runtime module contains the execution engine and task processing system for p2engine.

## Overview

The runtime is responsible for:

- Processing agent ticks (execution cycles)
- Managing asynchronous tasks via Celery
- Handling effects (side effects of agent actions)
- Running evaluation rollouts
- Implementing execution policies

## Architecture

```
runtime/
├── engine.py             # Main execution engine
├── agent_runtime.py      # Agent execution logic
├── handlers.py           # State handlers
├── effects.py            # Effect definitions
├── post_effects.py       # Post-execution hooks
├── helpers.py            # Runtime utilities
├── constants.py          # Configuration constants
├── policies/             # Execution policies
│   └── dedup.py         # Deduplication policies
├── tasks/                # Celery task definitions
│   ├── celery_app.py    # Celery configuration
│   ├── tasks.py         # Core tasks
│   ├── evals.py         # Evaluation tasks
│   ├── delegate_bridge.py # Agent communication
│   └── rollout_tasks.py # Rollout execution
├── task_runner/          # Task execution logic
│   ├── agent_runner.py  # Agent tick processing
│   └── constants.py     # Runner configuration
└── rollout/              # Evaluation rollout system
    ├── engine.py        # Rollout orchestration
    ├── spec.py          # Rollout specifications
    ├── expander.py      # Variant expansion
    └── store.py         # Rollout state storage
```

## Key Components

### Engine (`engine.py`)

The main orchestrator that starts all system components:

```python
from runtime.engine import Engine

# Initialize and start the engine
engine = Engine()
engine.start(block=True)  # Blocks until shutdown

# Components initialized:
# - Event loop for async operations
# - Session driver for conversation management
# - Agent registry with configured agents
# - Redis connections
# - Service container
```

### Agent Runtime (`agent_runtime.py`)

Processes agent execution cycles:

```python
class AgentRuntime:
    def __init__(self, agent, conversation_id, agent_id, stack):
        self.agent = agent
        self.conversation_id = conversation_id
        self.agent_id = agent_id
        self.stack = stack

    def step(self) -> Tuple[Optional[BaseState], List[BaseEffect]]:
        # 1. Get current state from stack
        # 2. Find appropriate handler
        # 3. Execute handler
        # 4. Return effects to execute
```

### State Handlers (`handlers.py`)

Each state type has a handler that processes it and produces effects:

```python
@handler(UserMessageState)
def handle_user_message(entry, stack, agent, conversation_id, agent_id):
    # 1. Create AskSchema with conversation history
    ask = AskSchema(history=render_for_llm(stack), conversation_id=conversation_id)

    # 2. Run the agent
    response = run_async(agent.run(ask))

    # 3. Materialize response (push states, create effects)
    return materialise_response(stack, response, conversation_id, agent_id)
```

#### Handler Types

1. **UserMessageState Handler**

   - Processes new user input
   - Calls agent with conversation history
   - Produces assistant response or tool calls

2. **ToolResultState Handler**

   - Processes tool execution results
   - May trigger reflection if configured
   - Continues conversation flow

3. **WaitingState Handler**

   - Monitors async operations
   - Handles timeouts
   - Cleans up expired operations

4. **AgentCallState Handler**

   - Initiates delegation to another agent
   - Sets up parent-child relationship
   - Creates correlation for response

5. **AgentResultState Handler**

   - Processes child agent responses
   - Updates parent conversation
   - May trigger completion

6. **FinishedState Handler**
   - Handles conversation completion
   - Triggers evaluations if configured
   - Notifies parent agents if delegated

### Effects (`effects.py`)

Effects represent side effects that need to be executed:

```python
@dataclass(slots=True, frozen=True)
class CallTool(BaseEffect):
    conversation_id: str
    agent_id: str
    branch_id: str
    tool_name: str
    parameters: dict
    tool_call_id: str
    tool_state_env: dict

    def execute(self, redis_client, celery_app):
        # Enqueue tool execution task
        celery_app.send_task(
            "runtime.tasks.tasks.execute_tool",
            args=[...],
            queue="tools"
        )
```

#### Effect Types

1. **CallTool**: Execute a tool function
2. **PushToAgent**: Send message to another agent
3. **PushAgentResult**: Return result to parent agent
4. **PublishSystemReply**: Send response to user

### Post Effects (`post_effects.py`)

Hooks that run after tool execution:

```python
@register_post_effect("agent_call")
def _agent_call_handler(*, stack, parameters, result, **kwargs):
    # Trigger agent delegation after tool execution
    child_id = parameters.get("agent_id")
    message = parameters.get("message")
    stack.push(AgentCallState(agent_id=child_id, message=message))
    return []  # No additional effects

@register_post_effect("treasurer_payment")
def _treasurer_payment_handler(*, result, parameters, **kwargs):
    # Reward agents based on evaluation score
    score = result.get("score", 0)
    if score >= 0.8:
        return [CallTool(...)]  # Transfer funds
    return []
```

### Task System (`tasks/`)

Celery-based asynchronous task processing:

#### Task Queues

1. **ticks**: Agent execution cycles (high volume)
2. **tools**: Tool function execution
3. **evals**: Evaluation processing
4. **rollouts**: Multi-variant testing

#### Core Tasks

```python
@app.task(name="runtime.tasks.tasks.process_session_tick")
def process_session_tick(conversation_id: str):
    # 1. Get all agents in conversation
    # 2. Process each agent's tick
    # 3. Re-enqueue if work remains

@app.task(name="runtime.tasks.tasks.execute_tool")
def execute_tool(conversation_id, agent_id, tool_name, parameters, ...):
    # 1. Get tool from registry
    # 2. Execute with parameters
    # 3. Store result in stack
    # 4. Trigger next tick
```

### Session Driver (`session_driver.py`)

Manages conversation lifecycle:

```python
def session_driver(poll_interval=1.0):
    while True:
        # 1. Check all active sessions
        # 2. Advance ticks when all agents ready
        # 3. Handle timeouts
        # 4. Clean up finished sessions
```

### Rollout System (`rollout/`)

A/B testing framework for agent configurations:

#### Rollout Specification

```yaml
teams:
  weather_team:
    initial_message: "What's the weather in Paris?"
    base:
      agent_id: agent_alpha
      tools: ["get_weather"]
    variants:
      - model: "openai/gpt-4o"
        temperature: 0.3
      - model: "openai/gpt-3.5-turbo"
        temperature: 0.7
    eval:
      evaluator_id: gpt4_judge
      metric: score
      rubric: "Rate helpfulness 0-1"
```

#### Rollout Execution

```python
# Expand variants
variants = expand_variants(team_spec)
# Produces: [{agent_id: "agent_alpha", model: "gpt-4o", ...}, ...]

# Run each variant
for variant in variants:
    # 1. Create conversation
    # 2. Apply overrides
    # 3. Send initial message
    # 4. Wait for completion
    # 5. Run evaluation
    # 6. Collect metrics
```

## Execution Flow

### 1. Conversation Tick

```
Session Driver → Check Active Sessions → Advance Tick
                                              ↓
                                     Process Agent Tick
                                              ↓
                                      Agent Runtime Step
                                              ↓
                                       State Handler
                                              ↓
                                    Generate Effects
                                              ↓
                                    Execute Effects
                                              ↓
                                   Update Redis State
```

### 2. Tool Execution Flow

```
CallTool Effect → Celery Queue → Tool Worker
                                      ↓
                               Execute Tool
                                      ↓
                              Store Result
                                      ↓
                             Post Effects
                                      ↓
                            Enqueue Next Tick
```

### 3. Agent Delegation Flow

```
PushToAgent Effect → Create Child Stack → Push Message
                                              ↓
                                    Process Child Agent
                                              ↓
                                     Child Completes
                                              ↓
                                 Bubble Result to Parent
```

## Configuration

### Constants (`constants.py`)

```python
TOOL_TIMEOUT_SEC = 30          # Tool execution timeout
MIN_AGENT_RESPONSE_SEC = 30    # Minimum agent response time
STACK_DUPLICATE_LOOKBACK = 100 # Deduplication window
MAX_STACK_LEN = 2000          # Maximum conversation length
MAX_REFLECTIONS = 3           # Self-reflection limit
MAX_ROUNDS = 3                # Idle round limit
```

### Environment Variables

```bash
# Execution
MAX_ROUNDS=3                  # Max idle rounds before throttle
MAX_REFLECTIONS=3             # Self-reflection iterations
TICK_FENCE_TTL=60            # Tick lock duration

# Deduplication
DEDUP_POLICY=none            # none|penalty|strict
STATE_GZIP_THRESH=2048       # Compression threshold

# Workers
CELERY_CONCURRENCY=4         # Worker processes
CELERY_PREFETCH=1            # Tasks per worker
```

## Policies

### Deduplication Policies (`policies/dedup.py`)

Prevent duplicate tool executions:

1. **NoDedupPolicy**: No deduplication (default)
2. **PenaltyDedupPolicy**: Log duplicates but allow
3. **StrictDedupPolicy**: Block duplicates unless side_effect_free

```python
# Tool configuration
@function_tool(
    name="my_tool",
    side_effect_free=True,  # Safe to call multiple times
    dedup_ttl=300,         # Dedup window in seconds
)
```

## Celery Configuration

### Worker Types

```bash
# Tick processor (high concurrency)
celery -A runtime.tasks.celery_app worker -Q ticks -c 16

# Tool executor (moderate concurrency)
celery -A runtime.tasks.celery_app worker -Q tools -c 8

# Eval processor (with beat scheduler)
celery -A runtime.tasks.celery_app worker -Q evals -c 4 --beat

# Rollout runner (low concurrency)
celery -A runtime.tasks.celery_app worker -Q rollouts -c 2
```

### Task Routing

```python
app.conf.task_routes = {
    "runtime.tasks.tasks.process_session_tick": {"queue": "ticks"},
    "runtime.tasks.tasks.execute_tool": {"queue": "tools"},
    "runtime.tasks.evals.run_eval": {"queue": "evals"},
    "runtime.tasks.rollout_tasks.run_variant": {"queue": "rollouts"},
}
```

## Best Practices

1. **Effect Execution**

   - Always execute effects through EffectExecutor
   - Handle effect failures gracefully
   - Use correlation IDs for async tracking

2. **State Management**

   - Mark conversations finished when complete
   - Clean up waiting states on timeout
   - Use branch-specific round counters

3. **Performance**

   - Limit conversation length with MAX_STACK_LEN
   - Use deduplication for expensive tools
   - Configure appropriate Celery concurrency

4. **Error Handling**

   - Implement timeout handlers for all async operations
   - Use WaitingState for proper cleanup
   - Log all state transitions

5. **Testing**
   - Use rollouts for A/B testing
   - Monitor metrics via artifact bus
   - Test timeout scenarios

## Extending the Runtime

### Custom Effects

```python
@dataclass(slots=True, frozen=True)
class MyCustomEffect(BaseEffect):
    my_field: str

    def execute(self, redis_client, celery_app):
        # Custom execution logic
        pass
```

### Custom Handlers

```python
from runtime.handlers import handler

@handler(MyCustomState)
def handle_my_custom_state(entry, stack, agent, conversation_id, agent_id):
    # Process state
    # Return effects
    return [MyCustomEffect(...)]
```

### Custom Post Effects

```python
@register_post_effect("my_post_effect")
def my_post_effect_handler(*, stack, parameters, result, **kwargs):
    # Run after tool execution
    return []  # Additional effects
```

## Monitoring

### Metrics

- Tick lag: Time between tick scheduling and execution
- Effect execution: Success/failure rates
- Tool latency: Execution time per tool
- Evaluation scores: Quality metrics

### Debugging

- Use `conversation watch` to monitor live
- Check `logs/main.log` for errors
- Inspect Redis keys for state
- Use artifact bus for event history
