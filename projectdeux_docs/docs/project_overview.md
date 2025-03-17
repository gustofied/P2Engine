# Multi-Agent System Project

## Project Overview

This repository manages a **multi-agent system** where different AI agents (e.g., `SimpleAgent`, `ChaosAgent`) exchange messages in a round-robin style. The conversation is logged in a structured JSON format for later analysis.

### Purpose

- Demonstrates how multiple AI agents interact.
- Captures each agent’s inputs and outputs in detail.
- Provides a modular system for extending or modifying agent behaviors.

## Key Components

### Agents

- **BaseAgent**: Abstract class (inherits from `SmartEntity`) requiring an `interact()` method.
- **SimpleAgent**: Implements a straightforward query to the LLM with no additional prompt engineering.
- **ChaosAgent**: Uses a more creative system prompt to generate chaotic or whimsical responses.

### LLM Integration

- **LLMClient**: A wrapper around `litellm` that handles:
  - API keys (from environment variables or explicit configuration).
  - Logging function (`my_custom_logging_fn`) to capture request/response events.

### Multi-Agent Scenario

- `multi_agent_scenario.py` & `multi_agent_scenario2.py`:
  - Manages multiple rounds of conversation among agents.
  - Logs the conversation flow to standard output and a file using Python’s logging.
  - Each scenario script sets up the agents, runs the conversation, and stores the final history.

### Entities & Management

- **SmartEntity**: A data class that any “intelligent” entity can inherit (e.g., Agents, Tools).
- **EntityManager**: Registers and tracks `SmartEntity` instances by their IDs.

### Logging

- `my_custom_logging_fn` (in `custom_logging/litellm_logger.py`):
  - Intercepts `litellm` calls to store each request (pre) and response (post) in `GLOBAL_LOG_DATA`.
  - Flushes logs into a JSON file upon exit (using `atexit`).
  - Creates a separate JSON file for each run (`litellm_log_<timestamp>.json`).

### Testing

- `tests/test_multi_agent_systems.py`:
  - Runs `multi_agent_conversation()` to ensure stability.
  - Could be expanded with assertions for expected output patterns.

## File & Directory Layout

```
.
├── custom_logging
│   └── litellm_logger.py        # Global logging structure for litellm calls
├── entities
│   ├── smart_entity.py         # Abstract class for intelligent entities
│   └── entity_manager.py       # Manages entity registration and lookup
├── integrations
│   └── llm
│       └── llm_client.py       # Wrapper for litellm, handles API calls & logging
├── single_agents
│   ├── base_agent.py           # Abstract BaseAgent
│   ├── simple_agent
│   │   └── agent.py            # Simple LLM-based agent
│   └── chaos_agent
│       └── agent.py            # Chaotic agent with whimsical system prompt
├── multi_agent_systems
│   ├── multi_agent_scenario.py # Example multi-agent scenario
│   └── multi_agent_scenario2.py # Alternative variation
├── tests
│   └── test_multi_agent_systems.py # Basic test runner
├── .env                        # Stores API keys (e.g., `OPENAI_API_KEY`)
└── requirements.txt            # Dependency list (optional)
```

## Detailed Review & Potential Improvements

### 1. Structure & Organization

#### Strengths

- Code is logically separated into modules (`agents`, `multi-agent system`, `logging`).
- Module naming (`single_agents`, `chaos_agent`) is clear and self-explanatory.
- Global logging structure (`litellm_logger.py`) is well-organized and tracks calls effectively.

#### Potential Improvements

- **File Naming Consistency**: Rename `litellm_lgger.py` to `litellm_logger.py` for consistency.
- **Top-Level Script**: Consider adding a `main.py` to orchestrate everything.
- **Types and Docstrings**: Add type hints and consistent docstrings for better maintainability.

### 2. Logging & Concurrency

#### Strengths

- Uses `atexit.register` to flush logs before exiting.
- Stores logs in JSON for machine-readable analysis.

#### Potential Improvements

- **Thread/Process Safety**: Use a threading lock in `litellm_logger.py` if running in parallel.
- **Multi-Process Handling**: Avoid file write collisions by using a shared queue or database logging.
- **Sensitive Data Handling**: Anonymize or redact user-sensitive data in logs.

### 3. Multi-Agent System Design

#### Strengths

- Implements a straightforward round-robin approach.
- Logs and stores conversation history for analysis.

#### Potential Improvements

- **Dynamic Conversations**: Instead of strict round-robin, allow agents to decide response order dynamically.
- **Persistence & Retrieval**: Write partial results to disk for longer experiments.
- **Integration with Tools**: Implement tool execution capabilities for agents.

### 4. Agents & BaseEntity

#### Strengths

- `BaseAgent` is properly abstract, forcing child classes to implement `interact()`.
- `SmartEntity` ensures agents are structured with an ID and potential connections.

#### Potential Improvements

- **Memory or State**: Implement a local memory for agents to retain context.
- **Error Handling**: Improve resilience against failed LLM calls (e.g., retries, fallback mechanisms).

### 5. Testing

#### Strengths

- Includes a test file ensuring basic functionality.

#### Potential Improvements

- **Unit vs. Integration Testing**:
  - Add unit tests for logging functions (`my_custom_logging_fn`).
  - Mock LLM API to test `LLMClient` without real API calls.
- **Assertions**:
  - Validate expected conversation patterns, not just execution success.

### 6. Environment & Deployment Considerations

- **Environment Variables**:
  - Centralize `.env` loading in a single script (`if __name__ == "__main__": load_dotenv()`).
- **API Key Security**:
  - Ensure `.env` is in `.gitignore`.
  - Use a secrets manager for production.
- **Deployment**:
  - Consider Dockerizing for a reproducible environment.

---

This structured markdown file provides a cleaner, organized view of your project documentation. Let me know if you'd like refinements!
