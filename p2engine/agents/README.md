# Agents Module

This module implements the core agent system for p2engine, providing different types of AI agents that can interact with users and each other.

## Overview

The agents module provides a flexible framework for creating and managing different types of agents:

- **LLM Agents**: AI-powered agents using language models
- **Rule-Based Agents**: Simple agents following predefined rules
- **Human-in-Loop Agents**: Agents that can request human intervention

## Architecture

```plaintext
agents/
├── impl/                       # Agent implementations
│   ├── llm_agent.py            # LLM-powered agent
│   ├── rule_agent.py           # Rule-based agent
│   └── human_in_loop_agent.py
├── templates/                  # Jinja2 templates for agent behaviors
│   ├── personas/               # Agent personality templates
│   ├── reflection/             # Self-reflection prompts
│   └── system_message.j2       # Core system prompt
├── agents.py                   # Agent factory and plugin manager
├── decorators.py               # Tool registration decorators
├── interfaces.py               # Protocol definitions
└── persona_registry.py         # Persona-to-tool mapping
```

## Key Concepts

### Agent Factory

The `AgentFactory` creates agents based on configuration, supporting dynamic plugin loading.

```python
# Example usage
factory = AgentFactory(llm_client, tool_registry, template_manager)
agent = factory.create(agent_config)
```

### Tool Registration

Tools are registered using the `@function_tool` decorator:

```python
from agents.decorators import function_tool
from pydantic import BaseModel

class WeatherInput(BaseModel):
    location: str
    unit: str = "fahrenheit"

@function_tool(
    name="get_weather",
    description="Get current weather",
    input_schema=WeatherInput,
    cache_ttl=300,  # Cache for 5 minutes
    side_effect_free=True,  # Safe to deduplicate
)
def get_weather(location: str, unit: str = "fahrenheit") -> dict:
    # Implementation
    return {
        "status": "success",
        "data": {"temperature": 72, "unit": unit}
    }
```

### Personas

Agents can have personas (defined in templates/personas/) that modify their behavior and automatically include required tools.

```yaml
# In persona_registry.py
REQUIRED_TOOLS = {
    "weather_expert": {"get_weather"},
    "financial_advisor": {"check_balance", "transfer_funds"},
    "researcher": {"web_search", "delegate"},
}
```

## Usage Example

```python
from orchestrator.schemas.schemas import AgentConfig, AskSchema
from agents.agents import AgentFactory

# Create an agent from configuration
agent_config = AgentConfig(
    id="assistant",
    type="llm",
    llm_model="openai/gpt-4o",
    tools=["get_weather", "delegate"],
    behavior_template="weather_expert"  # Optional persona
)

# Initialize factory
factory = AgentFactory(llm_client, tool_registry, template_manager)
agent = factory.create(agent_config)

# Run the agent
response = await agent.run(AskSchema(
    history=[{"role": "user", "content": "What's the weather in Paris?"}],
    conversation_id="conv_123"
))
```

## Agent Types

### LLM Agent (`impl/llm_agent.py`)

The most sophisticated agent type, powered by language models.

**Features:**

- Uses OpenAI-compatible APIs via litellm
- Supports function calling (tools)
- Can have behavior templates (personas)
- Supports reflection and self-critique
- Redis-based override system

**Configuration:**

```yaml
- id: my_llm_agent
  type: llm
  llm_model: "openai/gpt-4o"
  tools: ["get_weather", "delegate", "check_balance"]
  behavior_template: "helpful_assistant" # Optional
  temperature: 0.7 # Optional override
```

**Overrides:**

The LLM agent supports runtime overrides stored in Redis:

```python
# Set via CLI
p2engine config set-behavior conversation_name weather_expert
p2engine config set-tools conversation_name "get_weather,delegate"

# Or programmatically
redis.set(f"agent:{agent_id}:{conv_id}:override", json.dumps({
    "model": "openai/gpt-4o-mini",
    "temperature": 0.3,
    "tools": ["get_weather"],
    "behavior_template": "weather_expert"
}))
```

### Rule-Based Agent (`impl/rule_agent.py`)

Simple deterministic agent for testing and basic interactions.

**Features:**

- Pattern matching on user input
- Predefined responses
- No external dependencies
- Useful for testing

**Configuration:**

```yaml
- id: rule_bot
  type: rule_based
  rules:
    "hello": "Hi there! How can I help?"
    "weather": "I'm a simple bot, I can't check weather."
    "bye": "Goodbye!"
```

### Human-in-Loop Agent (`impl/human_in_loop_agent.py`)

Enables human intervention in conversations.

**Features:**

- Can escalate to human operators
- Supports callback URLs for notifications
- Placeholder responses while waiting

**Configuration:**

```yaml
- id: human_assisted
  type: human_in_loop
  callback_url: "https://example.com/notify" # Optional
```

## Template System

### System Message Template (`templates/system_message.j2`)

Core prompt that defines agent behavior:

```jinja2
You are an AI assistant designed to help users by answering questions
and performing actions using the tools provided.

{% if tools %}
Available tools:
{% for tool in tools %}
- **{{ tool.name }}**: {{ tool.description }}
{% endfor %}
{% endif %}
```

### Persona Templates (`templates/personas/`)

Modify agent behavior for specific roles:

```jinja2
# weather_expert.j2
You are a weather expert. When users ask about weather, use the
get_weather tool to provide accurate, detailed information. Include
relevant advice based on conditions.
```

### Reflection Templates (`templates/reflection/`)

Enable self-critique and improvement:

```jinja2
# self.j2
You previously answered:
"""{{ response }}"""

Reflect critically. If fully satisfactory, answer **GOOD**.
Otherwise, explain what could be improved.
```

## Plugin System

The agent system supports dynamic plugin loading via entry points:

```toml
# In pyproject.toml
[tool.poetry.plugins."agents"]
llm = "agents.impl.llm_agent:LLMAgent"
rule_based = "agents.impl.rule_agent:RuleBasedAgent"
custom = "my_package.agents:CustomAgent"  # Your custom agent
```

## Interfaces

The module defines protocols for extensibility:

```python
# From interfaces.py
class IAgent(Protocol):
    async def run(self, input: AskSchema) -> Union[ReplySchema, FunctionCallSchema]:
        ...

class ITool(Protocol):
    def execute(self, **kwargs) -> dict:
        ...
```

## Configuration

Agents are configured in `config/agents.yml`:

```yaml
agents:
  - id: agent_alpha
    type: llm
    llm_model: "openai/gpt-4o"
    behavior_template: null
    tools:
      - get_weather
      - delegate
      - check_balance
      - transfer_funds

  - id: agent_helper
    type: llm
    llm_model: "openai/gpt-4o"
    tools:
      - get_weather
      - check_balance

  - id: simple_bot
    type: rule_based
    rules:
      "help": "I can answer simple questions!"
```

## Best Practices

1. **Tool Selection**: Only include tools the agent actually needs
2. **Personas**: Use behavior templates for consistent role-playing
3. **Temperature**: Lower values (0.3-0.5) for factual tasks, higher (0.7-0.9) for creative
4. **Reflection**: Enable for critical tasks where accuracy matters
5. **Caching**: Use Redis overrides for temporary behavior changes

## Extending the System

To create a custom agent:

1. Implement the `IAgent` protocol
2. Register via entry points or manually
3. Add to configuration
4. Optionally create custom templates

```python
class MyCustomAgent:
    async def run(self, input: AskSchema) -> ReplySchema:
        # Custom logic here
        return ReplySchema(message="Custom response")
```
