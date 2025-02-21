# Project Overview

This project is a modular, robust multi-agent system that uses the **litellm** API to interact with language models. It is designed for scalability, extensive logging, and future visualization. The system comprises agents that utilize an LLM client, a custom logging mechanism that captures detailed API call data, and a multi-agent scenario demonstrating agent interactions.

---

# Core Components

## 1. Package Management & Environment Variables

- **Poetry** is used for dependency management and project configuration (see `pyproject.toml`).
- A **.env** file (git‑ignored) stores sensitive data like the `OPENAI_APY_KEY`, which is loaded using [python-dotenv](https://github.com/theskumar/python-dotenv).

## 2. LLM Client

- **Location:** `src/integrations/llm/llm_client.py`
- **Functionality:**  
  Wraps litellm calls, accepts parameters such as the model, API key, metadata, and passes them along with a custom logger function.

## 3. Custom Logging System

- **Location:** `src/custom_logging/litellm_logger.py`
- **Functionality:**
  - Converts litellm API call payloads into JSON‑serializable objects.
  - Organizes logs by run, agent, and individual calls (grouping pre‑call and post‑call events).
  - Uses an `atexit` handler to flush structured log data to a run‑specific JSON file in the `logs/` folder.
  - Extracts the agent ID from the payload (with fallbacks) so that entries are grouped under the correct agent instead of `"unknown_agent"`.

## 4. Agent Architecture

- **Abstract Base Agent:**  
  Located at `src/single_agents/base_agent.py`, it defines a common interface for all agents.
- **SimpleAgent:**  
  Located at `src/single_agents/simple_agent/agent.py`, it uses the LLM client to process user input and passes its agent ID via metadata for proper log grouping.
- **ChaosAgent:**  
  Located at `src/single_agents/chaos_agent/agent.py`, it employs a creative, unconventional system prompt to generate “chaotic” responses. It makes direct litellm calls with both system and user messages while logging its events.

## 5. Multi-Agent Scenario

- **Location:** `src/multi_agent_systems/multi_agent_scenario.py`
- **Functionality:**  
  Demonstrates an interactive scenario where SimpleAgent and ChaosAgent exchange messages. It simulates multi-agent communication that is logged using the robust logging system.

## 6. Testing

- **Location:** `tests/`  
  Contains test scripts such as `tests/test_simple_agent.py` and `tests/test_multi_agent_system.py` to simulate and verify agent interactions.

## 7. Future Visualization with Rerun.io

- **Planned Module:** `src/visualization/rerun_visualizer.py`
- **Functionality:**  
  Will read the structured JSON log file and visualize the agent interactions as a graph using Rerun’s GraphView. Nodes can represent agents and edges can represent API call events (pre/post events) over time.

---

# Project Directory Structure

projectdeux/
├── pyproject.toml # Poetry configuration & dependency management
├── README.md # Project overview, setup instructions, and design rationale
├── .env # Environment variables (e.g., OPENAI*APY_KEY)
├── logs/ # Directory for JSON log files (created at runtime)
│ └── litellm_log*<RUN_ID>.json # Run-specific, structured log file
├── src/
│ ├── integrations/ # External API integrations and tools
│ │ ├── **init**.py
│ │ └── llm/
│ │ ├── **init**.py
│ │ └── llm_client.py # LLM client module
│ ├── custom_logging/ # Custom logging modules
│ │ ├── **init**.py
│ │ └── litellm_logger.py # Custom logger for litellm API calls
│ ├── single_agents/ # Agent implementations
│ │ ├── **init**.py
│ │ ├── base_agent.py # Abstract base class for agents
│ │ ├── simple_agent/ # SimpleAgent implementation
│ │ │ ├── **init**.py
│ │ │ └── agent.py
│ │ └── chaos_agent/ # ChaosAgent implementation (creative responses)
│ │ ├── **init**.py
│ │ └── agent.py
│ └── multi_agent_systems/ # Multi-agent orchestration scenarios
│ ├── **init**.py
│ └── multi_agent_scenario.py # Demonstrates interaction between agents
├── tests/ # Test suite for your modules
│ ├── test_simple_agent.py
│ └── test_multi_agent_system.py
└── src/visualization/ # (Planned) Visualization module using Rerun SDK
└── rerun_visualizer.py # Will convert logs to a visual graph view

---

# Next Steps

1. **Visualization with Rerun.io**

   - Build the visualization module (`src/visualization/rerun_visualizer.py`) to read the structured log file and render a graph view of agent interactions over time.
   - Use Rerun’s GraphView (or other views like TextLogView) to display nodes (agents) and edges (API calls).

2. **Multi-Agent Orchestration & Communication**

   - Develop a coordination layer to manage and route interactions between multiple agents.
   - Consider role specialization (e.g., planner, executor) and implement interfaces for inter-agent communication.

3. **Persistent Memory & Context Management**

   - Implement session memory or a lightweight database (SQLite, Redis) to retain context over multiple interactions.
   - Use this to improve response coherence over longer conversations.

4. **Robust Error Handling & Asynchronous Processing**

   - Enhance error detection, implement retries or fallbacks, and integrate asynchronous API calls to boost performance.
   - Add monitoring and alerting for improved reliability.

5. **Testing & CI/CD**

   - Expand unit and integration tests.
   - Set up a CI/CD pipeline (using GitHub Actions, GitLab CI, etc.) to automate testing and deployment.

6. **Enhanced Documentation & Dashboard**
   - Expand the README and create a `docs/` folder with detailed guides, API references, and architecture diagrams.
   - Consider building a simple dashboard to visualize agent performance and log data in real time.

---

# Final Remarks

Your project now has a robust foundation with modular agents, extensive structured logging, and a clear path toward visualization and orchestration. Each component is designed to scale, allowing for the integration of additional APIs, complex multi-agent scenarios, and detailed error handling.

Feel free to extend this setup further, and enjoy the process of building out your multi-agent system!
