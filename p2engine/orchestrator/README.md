# Orchestrator Module

The orchestrator manages the flow of interactions between agents, users, and tools. It maintains conversation state and handles the execution flow.

## Overview

The orchestrator is responsible for:

- Managing interaction stacks (conversation history)
- Rendering conversations for LLMs
- Handling state transitions
- Managing tool and agent registries
- Supporting conversation branching

## Architecture

```
orchestrator/
├── interactions/          # Interaction management
│   ├── states/           # State machine states
│   │   ├── base.py      # Base state class
│   │   ├── user_message.py
│   │   ├── assistant_message.py
│   │   ├── tool_call.py
│   │   ├── tool_result.py
│   │   ├── agent_call.py
│   │   ├── agent_result.py
│   │   ├── waiting.py
│   │   └── finished.py
│   ├── stack.py         # Conversation stack management
│   ├── branch.py        # Branching support
│   ├── render.py        # LLM-compatible rendering
│   └── serializers.py   # State serialization
├── renderer/             # Template rendering
│   └── template_manager.py
├── schemas/              # Pydantic models
│   └── schemas.py
└── registries.py         # Agent and tool registries
```

## Key Components

### Interaction Stack

The `InteractionStack` is the core data structure that maintains conversation history with support for branching and persistence.

```python
from orchestrator.interactions import InteractionStack
from orchestrator.interactions.states.user_message import UserMessageState

# Create a stack for a conversation
stack = InteractionStack(redis_client, conversation_id, agent_id)

# Push states
stack.push(UserMessageState(text="Hello!"))
stack.push(AssistantMessageState(content="Hi! How can I help?"))

# Access history
current = stack.current()  # Latest state
length = stack.length()    # Number of states
entries = list(stack.iter_last_n(10))  # Last 10 entries

# Branching
new_branch = stack.fork(index=5)  # Create branch from index 5
stack.checkout("main")  # Switch branches
branches = stack.get_branch_info()  # List all branches
```

### States

The system uses a state machine with the following states:

#### Input States

- **UserMessageState**: User input

  ```python
  UserMessageState(text="What's the weather?", meta="optional metadata")
  ```

- **UserResponseState**: Response to agent questions
  ```python
  UserResponseState(text="Yes, please proceed")
  ```

#### Output States

- **AssistantMessageState**: Agent responses
  ```python
  AssistantMessageState(
      content="Here's the weather information",
      tool_calls=[{...}],  # Optional tool calls
      meta="reflection:weather"  # Optional metadata
  )
  ```

#### Tool States

- **ToolCallState**: Tool invocation

  ```python
  ToolCallState(
      id="unique_id",
      function_name="get_weather",
      arguments={"location": "Paris"}
  )
  ```

- **ToolResultState**: Tool execution result
  ```python
  ToolResultState(
      tool_call_id="unique_id",
      tool_name="get_weather",
      result={"status": "success", "data": {...}},
      reward=0.8  # Optional reward signal
  )
  ```

#### Agent Communication States

- **AgentCallState**: Request to another agent

  ```python
  AgentCallState(
      agent_id="helper_agent",
      message="Please analyze this data"
  )
  ```

- **AgentResultState**: Response from another agent
  ```python
  AgentResultState(
      correlation_id="correlation_id",
      result={"status": "success", "content": "Analysis complete"},
      score=0.9  # Optional quality score
  )
  ```

#### Control States

- **WaitingState**: Async operation tracking

  ```python
  WaitingState(
      kind="tool",  # or "agent", "llm", "user_input"
      deadline=time.time() + 30,
      correlation_id="operation_id"
  )
  ```

- **FinishedState**: Conversation completion
  ```python
  FinishedState()  # Terminal state
  ```

### Rendering System

The rendering system converts conversation history into LLM-compatible formats:

```python
from orchestrator.interactions.render import render_for_llm

# Basic rendering
messages = render_for_llm(stack, last_n=10)
# Returns OpenAI-format messages:
# [
#   {"role": "user", "content": "Hello"},
#   {"role": "assistant", "content": "Hi!"},
#   {"role": "tool", "tool_call_id": "123", "content": "{...}"}
# ]

# With policies
messages = render_for_llm(
    stack,
    last_n=20,
    policy_name="summary",  # Custom rendering policy
    exclude_types=[WaitingState]  # Exclude certain states
)
```

### Branching System

Support for exploring multiple conversation paths:

```python
from orchestrator.interactions.branch import fork, checkout, rewind

# Create a new branch from current position
new_branch_id = fork(stack, index=10)

# Switch branches
checkout(stack, "main")
checkout(stack, new_branch_id)

# Rewind current branch (destructive)
rewind(stack, index=5)

# Fork with custom name
stack.fork(index=7)  # Creates branch with auto-generated ID
```

### Serialization

States are serialized for Redis storage with compression support:

```python
from orchestrator.interactions.serializers import encode, decode

# Encoding
state = UserMessageState(text="Long message...")
envelope = encode(state)
# {
#   "v": 1,  # Version
#   "t": "UserMessageState",  # Type
#   "ts": 1234567890.123,  # Timestamp
#   "data": "...",  # Compressed if > 2KB
#   "compressed": true
# }

# Decoding
restored_state = decode(envelope)
```

## State Flow Diagram

```
┌─────────────┐
│ UserMessage │
└──────┬──────┘
       ↓
┌──────────────────┐     ┌──────────┐
│ AssistantMessage ├────→│ Finished │
└────────┬─────────┘     └──────────┘
         ↓
    ┌────┴────┐
    │         │
┌───▼──┐  ┌──▼────────┐
│ Tool │  │AgentCall  │
│ Call │  │           │
└───┬──┘  └──┬────────┘
    │        │
┌───▼────┐ ┌─▼─────┐
│Waiting │ │Waiting│
└───┬────┘ └─┬─────┘
    │        │
┌───▼────┐ ┌─▼──────────┐
│Tool    │ │Agent       │
│Result  │ │Result      │
└───┬────┘ └─┬──────────┘
    │        │
    └────┬───┘
         ↓
   (Back to AssistantMessage)
```

## Registries

### Tool Registry

Manages available tools:

```python
from orchestrator.registries import tool_registry

# Register a tool
tool_registry.register(my_tool)

# Get tool by name
weather_tool = tool_registry.get_tool_by_name("get_weather")

# List all tools
tools = tool_registry.get_tools()
tool_names = tool_registry.list_tools()  # Dict of name -> description
```

### Agent Registry

Manages agent instances with Redis persistence:

```python
from orchestrator.registries import AgentRegistry

registry = AgentRegistry(repository, agent_factory)

# Register agent
registry.register(agent, config)

# Get agent (lazy loads from config if needed)
agent = registry.get_agent("agent_alpha")

# List registered agents
agents = registry.list_agents()  # Dict of id -> type
```

## Artifact Integration

The stack automatically publishes artifacts for each state:

```python
# Each pushed state creates an artifact
stack.push(UserMessageState(text="Hello"))
# Creates artifact with:
# - Unique ref
# - Session/branch/episode IDs
# - Timestamp
# - State data
# - Metadata

# Special handling for tool calls
stack.push(ToolCallState(id="123", ...))
# Stores tool call reference for correlation

# Parent-child tracking for agent calls
stack.push(AgentCallState(agent_id="child", ...))
# Sets up parent-child relationship in Redis
```

## Configuration

### Agent Configuration Schema

```python
@dataclass
class LLMAgentConfig:
    type: Literal["llm"]
    id: str
    llm_model: str = "openai/gpt-4o"
    behavior_template: Optional[str] = None
    tools: List[str] = []
    render_policy: Optional[str] = None
    enable_self_reflection: bool = False
    reflection_agent_id: Optional[str] = None
```

### Tool Configuration Schema

```python
@dataclass
class ToolConfig:
    name: str
    description: str
    input_schema: Optional[Type[BaseModel]] = None
    output_schema: Optional[Type[BaseModel]] = None
    post_effects: Optional[List[str]] = None
    requires_context: bool = False
    cache_ttl: Optional[int] = None
    side_effect_free: bool = False
    dedup_ttl: Optional[int] = None
    reflect: bool = False
```

## Best Practices

1. **State Management**

   - Always push states in logical order
   - Use WaitingState for async operations
   - Mark conversations finished when complete

2. **Branching**

   - Use branches for exploring alternatives
   - Fork before destructive operations
   - Clean up old branches periodically

3. **Rendering**

   - Limit history with last_n for context windows
   - Exclude internal states from LLM view
   - Use render policies for specialized formats

4. **Performance**

   - States are compressed automatically if > 2KB
   - Use Redis TTLs for automatic cleanup
   - Prune old branches with conversation prune command

5. **Error Handling**
   - Always handle WaitingState timeouts
   - Check for FinishedState before operations
   - Validate state transitions

## Extension Points

### Custom States

Create new states by extending BaseState:

```python
from orchestrator.interactions.states.base import BaseState
from dataclasses import dataclass

@dataclass(slots=True, frozen=True)
class CustomState(BaseState):
    custom_field: str
    optional_field: Optional[int] = None

    __version__: ClassVar[int] = 1  # For migration support
```

### Custom Render Policies

Add rendering policies for special formats:

```python
from orchestrator.interactions.render_policies import register_policy

@register_policy("summary")
def summary_policy(messages: List[Dict], **kwargs) -> List[Dict]:
    # Custom rendering logic
    return summarized_messages
```

### State Handlers

The runtime uses handlers to process states - see runtime module for details.
