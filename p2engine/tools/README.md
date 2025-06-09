# Tools Module

Tools are functions that agents can call to interact with external systems or perform computations.

## Overview

Tools extend agent capabilities by providing:

- External API access (weather, web search, etc.)
- Inter-agent communication (delegate)
- Ledger operations (transfers, balance checks)
- Custom business logic
- Computational functions

## Architecture

```
tools/
├── __init__.py          # Auto-discovery and registration
├── constants.py         # Shared constants (HELPER_KWARGS)
├── delegate_tool.py     # Agent-to-agent delegation
├── ledger_tools.py      # Canton blockchain integration
├── weather_tool.py      # Weather API example
└── league_tool.py       # Sports data example
```

## Creating Tools

### Basic Tool Structure

```python
from pydantic import BaseModel, Field
from agents.decorators import function_tool

# 1. Define input schema (optional but recommended)
class MyToolInput(BaseModel):
    required_param: str
    optional_param: int = Field(default=10, description="Optional parameter")

    # Validation
    @validator("required_param")
    def validate_param(cls, v):
        if not v.strip():
            raise ValueError("Parameter cannot be empty")
        return v

# 2. Create the tool function
@function_tool(
    name="my_tool",
    description="Does something useful",
    input_schema=MyToolInput,
    cache_ttl=60,  # Cache for 60 seconds
    side_effect_free=True,  # Safe to deduplicate
    requires_context=False,  # Only gets explicit params
    post_effects=["save_artifact"],  # Run after execution
    dedup_ttl=10,  # Dedup window
    reflect=False,  # No reflection needed
)
def my_tool(required_param: str, optional_param: int = 10) -> dict:
    """
    Tool implementation.

    Returns dict with:
    - status: "success" or "error"
    - data: Tool-specific data (optional)
    - message: Human-readable message
    - error_type: Error classification (if error)
    """
    try:
        # Tool logic here
        result = process_data(required_param, optional_param)

        return {
            "status": "success",
            "data": {
                "result": result,
                "processed_at": datetime.now().isoformat()
            },
            "message": f"Successfully processed {required_param}"
        }
    except ValueError as e:
        return {
            "status": "error",
            "message": str(e),
            "error_type": "validation_error"
        }
    except Exception as e:
        logger.error(f"Tool failed: {e}")
        return {
            "status": "error",
            "message": "Internal error occurred",
            "error_type": "internal_error"
        }
```

### Tool Configuration Options

#### Input Schema

```python
input_schema=MyToolInput  # Pydantic model for validation
# or None for simple tools
```

#### Caching

```python
cache_ttl=300  # Cache results for 5 minutes
# Results cached by parameter hash
# Cache key: tool_cache:{name}:{param_hash}
```

#### Context Requirements

```python
requires_context=True  # Receives all context
# Gets: conversation_id, creator_id, branch_id, redis_client
# Plus all user parameters

requires_context=False  # Only user parameters (default)
# Cleaner for pure functions
```

#### Side Effects

```python
side_effect_free=True  # No external changes
# Can be safely retried/deduplicated
# Examples: read operations, calculations

side_effect_free=False  # Makes changes (default)
# Examples: transfers, writes, API calls
```

#### Deduplication

```python
dedup_ttl=60  # Prevent duplicate calls for 60s
# Works with dedup policies (none/penalty/strict)
# Key: dedup:{conv}:{agent}:{branch}:{tool_hash}
```

#### Post Effects

```python
post_effects=["agent_call"]  # Run after tool
# Available post effects:
# - agent_call: Trigger delegation
# - treasurer_payment: Reward based on score
# - save_artifact: Store results (placeholder)
# - raise_event: Emit event (placeholder)
```

#### Reflection

```python
reflect=True  # Agent reflects on tool output
# Adds reflection prompt after execution
# Useful for critical operations
```

## Built-in Tools

### Delegate Tool (`delegate_tool.py`)

Enables agent-to-agent communication within the same conversation.

```python
@function_tool(
    name="delegate",
    description="Spawn or wake another agent in the same conversation",
    input_schema=DelegateInput,
    post_effects=["agent_call"],
    requires_context=True,
    side_effect_free=True,
)
def delegate(agent_id: str, message: str, conversation_id: str, **_):
    # Queues message to target agent
    # Returns immediately
    # Child agent processes asynchronously
    return {"status": "queued", "child": agent_id}
```

**Usage Example:**

```
User: What's the weather in Paris and Tokyo?
Agent: I'll check that for you.
  → delegate(agent_id="weather_helper", message="Get weather for Paris")
  → delegate(agent_id="weather_helper", message="Get weather for Tokyo")
```

### Ledger Tools (`ledger_tools.py`)

Canton blockchain integration for agent wallets and transfers.

#### Transfer Funds

```python
@function_tool(
    name="transfer_funds",
    description="Transfer funds from your wallet to another agent's wallet",
    input_schema=TransferInput,
    requires_context=True,
    side_effect_free=False,
    dedup_ttl=10,  # Prevent double transfers
)
def transfer_funds(to_agent: str, amount: float, reason: str = "",
                  creator_id: str = "", conversation_id: str = "", **kwargs):
    # Validates amount (must be positive, <= 10000)
    # Ensures both wallets exist
    # Executes Canton transfer
    # Returns transaction details
```

#### Check Balance

```python
@function_tool(
    name="check_balance",
    description="Check the current balance of an agent's wallet",
    input_schema=BalanceInput,
    requires_context=True,
    side_effect_free=True,  # Read-only
    cache_ttl=30,  # Cache for 30s
)
def check_balance(agent_id: Optional[str] = None, creator_id: str = "", **kwargs):
    # Defaults to checking own balance
    # Creates wallet if doesn't exist
    # Returns formatted balance
```

#### Transaction History

```python
@function_tool(
    name="transaction_history",
    description="Get your recent transaction history",
    input_schema=HistoryInput,
    requires_context=True,
    side_effect_free=True,
    cache_ttl=60,
)
def transaction_history(limit: int = 10, creator_id: str = "", **kwargs):
    # Returns recent transactions
    # Shows sent/received with parties
    # Includes reasons and timestamps
```

#### Reward Agent

```python
@function_tool(
    name="reward_agent",
    description="Reward another agent for good performance",
    input_schema=RewardInput,
    requires_context=True,
    side_effect_free=False,
)
def reward_agent(agent_id: str, amount: float = 10.0,
                reason: str = "Good work!", creator_id: str = "", **kwargs):
    # Simplified transfer for rewards
    # Adds "Reward: " prefix to reason
    # Same validation as transfer_funds
```

### Weather Tool (`weather_tool.py`)

Example external API integration.

```python
@function_tool(
    name="get_weather",
    description="Get the current weather in a given location",
    input_schema=WeatherInput,
)
def get_weather(location: str, unit: str = "fahrenheit") -> dict:
    # Mock implementation
    # Real implementation would call weather API
    # Handles unit conversion
    # Returns temperature and conditions
```

### League Tool (`league_tool.py`)

Example data lookup tool.

```python
@function_tool(
    name="get_league_leader",
    description="Get the current leader of a football league",
    input_schema=LeagueInput,
)
def get_league_leader(league: str) -> dict:
    # Returns league standings
    # Mock data for examples
    # Could integrate with sports APIs
```

## Tool Response Format

All tools must return a dictionary with this structure:

```python
{
    "status": "success" | "error",  # Required
    "data": {                       # Optional, tool-specific
        "any": "data",
        "here": 123
    },
    "message": "Human readable",    # Optional but recommended
    "error_type": "category",       # Required if error
    "cost_usd": 0.002,             # Optional, for metrics
    "cache_status": "hit" | "miss"  # Set automatically
}
```

### Success Response

```python
{
    "status": "success",
    "data": {
        "temperature": 72,
        "conditions": "sunny"
    },
    "message": "Weather retrieved successfully"
}
```

### Error Response

```python
{
    "status": "error",
    "message": "City not found",
    "error_type": "not_found_error"
}
```

## Tool Registration

Tools are automatically discovered and registered on import:

```python
# In tools/__init__.py
def load_tools():
    # Scan directory for .py files
    # Import each module
    # Tools self-register via decorator
    # Errors logged but don't stop loading
```

### Manual Registration

```python
from orchestrator.registries import tool_registry
from agents.decorators import FunctionTool

# Create tool instance
tool = FunctionTool(my_function, tool_config)

# Register
tool_registry.register(tool)
```

## Context Parameters

When `requires_context=True`, tools receive:

```python
def my_context_tool(
    # User parameters
    user_param: str,
    # Context parameters (automatic)
    conversation_id: str,      # Current conversation
    creator_id: str,          # Calling agent ID
    branch_id: str,           # Conversation branch
    redis_client: redis.Redis,  # Redis connection
    **kwargs  # Future compatibility
):
    pass
```

## Post Effects System

Post effects run after successful tool execution:

### Built-in Post Effects

#### agent_call

```python
# Triggers after delegate tool
# Pushes AgentCallState to stack
# Enqueues next conversation tick
```

#### treasurer_payment

```python
# Rewards agents based on evaluation
# Only if score >= threshold
# Triggers transfer_funds tool
```

### Custom Post Effects

```python
from runtime.post_effects import register_post_effect

@register_post_effect("my_effect")
def my_effect_handler(*,
                     conversation_id: str,
                     agent_id: str,
                     stack: InteractionStack,
                     parameters: dict,
                     result: dict,
                     redis_client: redis.Redis) -> List[BaseEffect]:
    # Process after tool execution
    # Return additional effects
    if result.get("data", {}).get("needs_help"):
        return [PushToAgent(...)]
    return []
```

## Caching System

Tool results can be cached in Redis:

```python
# Cache key format
tool_cache:{tool_name}:{sha1(params)}

# Cache storage
{
    "status": "success",
    "data": {...},
    "message": "...",
    # Note: cache_status NOT stored
}

# Usage
@function_tool(cache_ttl=300)  # 5 minutes
def expensive_calculation(x: int) -> dict:
    # First call: executes and caches
    # Subsequent calls: returns cached
    # After TTL: executes again
```

## Error Handling

### Best Practices

1. **Validate inputs early**

   ```python
   if amount <= 0:
       return {"status": "error", "message": "Amount must be positive"}
   ```

2. **Classify errors**

   ```python
   error_type = "validation_error"  # User error
   error_type = "not_found_error"   # Missing resource
   error_type = "permission_error"  # Access denied
   error_type = "internal_error"    # System error
   ```

3. **Log internal errors**

   ```python
   except Exception as e:
       logger.error(f"Tool {tool_name} failed: {e}")
       return {"status": "error", ...}
   ```

4. **Provide helpful messages**
   ```python
   "message": "Transfer failed: Insufficient balance (50 < 100)"
   ```

## Testing Tools

### Unit Testing

```python
def test_my_tool():
    result = my_tool(required_param="test", optional_param=5)
    assert result["status"] == "success"
    assert result["data"]["result"] == expected
```

### Integration Testing

```python
# Via chat
p2engine chat with agent_alpha
> Use my_tool with parameter "test"

# Via rollout
teams:
  tool_test:
    initial_message: "Test my_tool with various inputs"
    variants:
      - tools: ["my_tool"]
```

### Manual Testing

```python
# In Python shell
from tools.my_tool import my_tool
result = my_tool("test", 5)
print(result)
```

## Performance Considerations

1. **Caching**

   - Cache expensive operations
   - Set appropriate TTLs
   - Monitor cache hit rates

2. **Deduplication**

   - Use dedup_ttl for critical tools
   - Set side_effect_free correctly
   - Monitor duplicate attempts

3. **Timeouts**

   - Tools have 30s timeout (TOOL_TIMEOUT_SEC)
   - Return quickly or use async patterns
   - Handle timeouts gracefully

4. **Resource Usage**
   - Close connections properly
   - Limit memory usage
   - Use streaming for large data

## Best Practices

1. **Tool Design**

   - Single responsibility
   - Clear, descriptive names
   - Comprehensive descriptions
   - Predictable behavior

2. **Input Validation**

   - Use Pydantic schemas
   - Validate early
   - Provide clear error messages
   - Set sensible defaults

3. **Error Handling**

   - Always return status
   - Classify errors
   - Log internal errors
   - Don't expose internals

4. **Documentation**

   - Document parameters
   - Provide usage examples
   - Explain side effects
   - Note any limitations

5. **Security**
   - Validate all inputs
   - Check permissions
   - Rate limit if needed
   - Audit sensitive operations
