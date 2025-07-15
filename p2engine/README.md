# P2Engine: A Multi-Agent System Framework

<div align="center">

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blueviolet)](https://python-poetry.org/)
[![Redis](https://img.shields.io/badge/cache-redis-red)](https://redis.io/)
[![Celery](https://img.shields.io/badge/task%20queue-celery-green)](https://docs.celeryproject.org/)
[![Daml](https://img.shields.io/badge/ledger-daml-blue)](https://www.digitalasset.com/developers)

**Orchestration – Observability – Adaptation – Auditability**

</div>

## 🌟 Overview

P2Engine is a multi-agent system framework that aims to be fully agentic, emergent, and trustworthy. Under continuous development, its core mission is to achieve complete autonomy. To do so it explore various implementations, including:


### Core Implementations

- **FSM Orchestration**: Finite-state machine coordination enabling precise, observable agent workflows
- **Audit Layer via DLT**: Canton/Daml integration providing immutable audit trails and privacy-aware operations
- **Adaptation**: MCTS/RL-based reasoners with automated evaluation for continuous improvement
- **Distributed Task Execution**: Celery-based architecture for scalable agent operations
- **Effect System**: Controlled side-effect management ensuring system integrity
- **Observability**: Real-time monitoring, tracing, and debugging capabilities


## 🏗️ Architecture

P2Engine is organized into several core modules, each with its own comprehensive documentation:

### Core Modules

- **[`/agents`](./agents/README.md)** - Agent implementations and framework

  - LLM, rule-based, and human-in-loop agents
  - Tool registration and decorators
  - Persona system and templates
  - Agent factory and plugin system

- **[`/orchestrator`](./orchestrator/README.md)** - Conversation flow management

  - Interaction stack with branching support
  - State machine and transitions
  - LLM-compatible message rendering
  - Agent and tool registries

- **[`/runtime`](./runtime/README.md)** - Execution engine and task processing

  - Agent runtime and state handlers
  - Effect system for side effects
  - Celery-based task distribution
  - Rollout and evaluation execution

- **[`/infra`](./infra/README.md)** - Core infrastructure components

  - Configuration management
  - Artifact bus for event storage
  - LLM client abstraction
  - Evaluation framework
  - Session management

- **[`/tools`](./tools/README.md)** - Extensible tool system

  - Tool creation guide
  - Built-in tools (delegate, ledger, weather)
  - Caching and deduplication
  - Post-effects system


### System Flow

1. **Agents** execute tasks based on FSM-defined workflows
2. **Orchestrator** manages state transitions and coordination
3. **Runtime** handles execution, effects, and learning feedback
4. **DLT** provides verifiable infrastructure for all operations
5. **Evaluators** assess quality and trigger adaptation
6. **Reasoners** optimize future strategies based on outcomes

### Understanding the System

For a deep understanding of P2Engine:

1. **Start with [`/agents/README.md`](./agents/README.md)** to understand how agents work
2. **Read [`/orchestrator/README.md`](./orchestrator/README.md)** to learn about conversation flow
3. **Study [`/runtime/README.md`](./runtime/README.md)** for execution details
4. **Review [`/tools/README.md`](./tools/README.md)** to create custom tools
5. **Check [`/infra/README.md`](./infra/README.md)** for infrastructure details

## 🚀 Quick Start

### Prerequisites

- Python 3.9+
- Redis
- Poetry (for dependency management)
- Daml SDK (optional, for ledger features)
- OpenAI API key

### Installation

```bash
# Clone the repository
git clone <repository-url>
cd p2engine

# Install dependencies
poetry install

# Set up environment variables
cp .env.example .env
# Edit .env with your configuration (see Environment Configuration below)

# Initialize Canton/Daml (optional, for ledger features)
./scripts/setup_canton.sh
```

### Environment Configuration (.env)

The `.env` file contains all critical configuration for the system. Here's a complete guide:

```bash
# Configuration file path (optional - defaults to config/config.json)
CONFIG_FILE=config/config.json

# OpenAI API Configuration (REQUIRED)
# Get your API key from: https://platform.openai.com/api-keys
OPENAI_API_KEY="sk-your-api-key-here"

# Canton/Ledger Configuration
# Set to false to run without financial ledger features (faster startup)
LEDGER_ENABLED=true

# Daml Package ID (auto-generated when building Daml project)
# This is set automatically by run_project.sh when ledger is enabled
DAML_PACKAGE_ID=auto_generated_on_build

# Logging Configuration
LOG_LEVEL=INFO              # Main application log level
WORKER_LOG_LEVEL=INFO       # Celery worker log level
LITELLM_LOG_LEVEL=error     # LLM library log level (set to debug for API traces)
LOG_TO_CONSOLE=0            # Set to 1 to see logs in console

# Redis Configuration (optional - these are the defaults)
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0

# Tool Deduplication Policy
# Options:
#   - none: No deduplication, all tool calls execute
#   - penalty: Track duplicates but allow execution
#   - strict: Block duplicate side-effect operations
DEDUP_POLICY=none

# Artifact Storage Driver
# Options:
#   - fs: Filesystem storage (default, no setup required)
#   - s3: AWS S3 storage (requires S3_BUCKET env var)
ARTIFACT_DRIVER=fs

# Development/Debugging Options
# LOG_TO_CONSOLE=1           # Show logs in terminal
# LITELLM_LOG_LEVEL=debug    # See all LLM API calls
# LEDGER_DEV_MODE=true       # Auto-set for development
```

### Running the System

The **primary way** to run P2Engine is through the orchestration script:

```bash
# This single command starts EVERYTHING:
./scripts/run_project.sh
```

#### What run_project.sh does:

1. **Environment Setup**: Loads `.env` configuration
2. **Process Cleanup**: Kills any existing P2Engine processes
3. **Redis Initialization**: Starts Redis and clears the database
4. **Canton/Ledger Setup** (if LEDGER_ENABLED=true):
   - Builds the Daml project
   - Extracts and sets DAML_PACKAGE_ID
   - Starts Canton daemon
   - Launches JSON API
   - Initializes agent wallets
5. **Celery Workers**: Starts 4 worker queues:
   - `ticks`: Main orchestration queue (16 workers)
   - `tools`: Tool execution queue (16 workers)
   - `evals`: Evaluation queue (8 workers + beat scheduler)
   - `rollouts`: Rollout execution queue (2 workers)
6. **Engine**: Starts the main runtime engine
7. **CLI**: Launches the interactive shell

The script handles all the complex orchestration and provides:

- Automatic log rotation with timestamped directories
- Process monitoring with PIDs
- Graceful shutdown on Ctrl+C
- Health checks for all services

#### Manual Component Start (Advanced)

If you need to run components separately for debugging:

```bash
# 1. Redis
redis-server

# 2. Canton (if using ledger)
./scripts/start_canton.sh

# 3. Celery workers
poetry run celery -A runtime.tasks.celery_app worker -Q ticks -n ticks@%h
poetry run celery -A runtime.tasks.celery_app worker -Q tools -n tools@%h
poetry run celery -A runtime.tasks.celery_app worker -Q evals -n evals@%h
poetry run celery -A runtime.tasks.celery_app worker -Q rollouts -n rollouts@%h

# 4. Engine
poetry run python runtime/engine.py

# 5. CLI
poetry run p2engine shell
```

## 💬 Basic Usage

### Starting a Chat

```bash
# Start a conversation with an agent
p2engine chat with agent_alpha

# In the chat:
You> Hello! What can you do?
You> Check my balance
You> Transfer 25 to agent_beta for helping with analysis
You> What's the weather in Paris?
```

### Multi-Agent Delegation

```bash
# Agents can delegate to each other
You> Delegate to agent_helper: What's the weather in Tokyo?
You> If they did well, reward them 20 units
```

### Using the Shell

```bash
p2engine shell

# Available commands:
p2engine▸ agent list
p2engine▸ conversation list
p2engine▸ ledger balance agent_alpha
p2engine▸ rollout start config/demo_rollout.yml
```

## 💰 Ledger Operations

P2Engine includes a full financial ledger system powered by Canton/Daml:

### Initialize Wallets

```bash
# Initialize all agent wallets with starting balance
p2engine ledger init --balance 100.0
```

### Check Balances

```bash
# Check specific agent balance
p2engine ledger balance agent_alpha

# Check system metrics
p2engine ledger metrics

# View all wallets
p2engine ledger overview
```

### Transfer Funds

```bash
# Direct transfer via CLI
p2engine ledger transfer agent_alpha agent_beta 25.0 --reason "Payment for services"

# Or through agent conversation
p2engine chat with agent_alpha
You> Transfer 50 to treasurer for management fees
```

### Transaction History

```bash
# View agent's transaction history
p2engine ledger history agent_alpha --limit 20

# Audit trail for all ledger events
p2engine ledger audit
```

## 🧪 Learning-Enabled System

The rollout system enables continuous improvement through evaluation and adaptation:

### Example Learning Configuration

```yaml
# config/learning_rollout.yml
teams:
  autonomous_team:
    initial_message: "Solve this complex multi-step problem"
    base:
      agent_id: agent_alpha
      model: openai/gpt-4o
      reasoning_policy: mcts_v1
    variants:
      - tools: ["analyze", "delegate", "verify"]
        temperature: 0.3
        search_depth: 10
      - tools: ["analyze", "delegate", "verify", "learn"]
        temperature: 0.7
        search_depth: 20
    eval:
      evaluator_id: comprehensive_judge
      metrics: ["correctness", "efficiency", "collaboration"]
      feedback_loop: true
      rubric: |
        Evaluate based on:
        - Solution correctness (0.4)
        - Execution efficiency (0.3)
        - Effective delegation (0.3)
```

### Running Rollouts

```bash
# Start a rollout
p2engine rollout start config/rollout_joke.yml --follow

# View results
p2engine eval top <session_id> --metric score
```

## 🛠️ Creating Custom Tools

Tools extend agent capabilities. Here's how to create one:

```python
# tools/my_custom_tool.py
from pydantic import BaseModel
from agents.decorators import function_tool

class MyToolInput(BaseModel):
    query: str
    limit: int = 10

@function_tool(
    name="search_database",
    description="Search the knowledge database",
    input_schema=MyToolInput,
    cache_ttl=300,  # Cache for 5 minutes
    side_effect_free=True,
)
def search_database(query: str, limit: int = 10) -> dict:
    # Implementation here
    results = perform_search(query, limit)
    return {
        "status": "success",
        "data": results,
        "count": len(results)
    }
```

## 🎯 Advanced Features

### Branch Management

```bash
# View conversation branches
p2engine conversation branches <conversation_name>

# Rewind to a previous state
p2engine conversation rewind <conversation_name> 10 --branch

# Checkout a different branch
p2engine conversation checkout <conversation_name> <branch_id>
```

### Real-time Monitoring

```bash
# Watch conversation stack in real-time
p2engine conversation watch <conversation_name>

# Monitor artifacts
p2engine artifact show <conversation_id> --limit 50
```

### Configuration Overrides

```bash
# Change agent behavior
p2engine config set-behavior <conversation> weather_expert

# Override tools
p2engine config set-tools <conversation> get_weather,delegate,check_balance

# View current overrides
p2engine config show-overrides <conversation>
```

## 📊 Evaluation System

P2Engine includes a sophisticated evaluation framework:

### Built-in Evaluators

- **gpt4_judge**: General-purpose quality evaluation
- Custom rubrics for specific use cases

### Creating Custom Evaluators

```python
from infra.evals.llm_eval import LLMEvaluator
from infra.evals.registry import evaluator

@evaluator(id="domain_expert", version="1.0")
class DomainExpertEvaluator(LLMEvaluator):
    model = "openai/gpt-4o"

    def build_messages(self, payload):
        # Custom evaluation logic
        return [...]
```

## 🔧 Configuration

### Main Configuration (`config/config.json`)

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
      "default_model": "openai/gpt-4o"
    }
  },
  "ledger": {
    "enabled": true,
    "json_api_url": "http://localhost:7575",
    "party_id": "p2engine::default",
    "initial_balance": 100.0
  }
}
```

### Agent Configuration (`config/agents.yml`)

```yaml
agents:
  - id: agent_alpha
    type: llm
    llm_model: "openai/gpt-4o"
    tools: ["get_weather", "delegate", "check_balance", "transfer_funds"]

  - id: treasurer
    type: llm
    llm_model: "openai/gpt-4o"
    behavior_template: "financial_expert"
    tools: ["check_balance", "transfer_funds", "transaction_history"]
```

## 🧪 Testing Scenarios

### Multi-Agent Collaboration Test

```bash
p2engine chat with agent_alpha

# Test delegation chain
You> Check my balance
You> Delegate to treasurer: Please distribute 100 units equally among agent_beta, agent_helper, and child
You> Check my balance after delegation
You> Show all recent transactions
```

### Concurrent Operations Test

```bash
# Terminal 1
p2engine chat with agent_alpha
You> Transfer 50 to agent_beta

# Terminal 2 (simultaneously)
p2engine chat with agent_beta
You> Transfer 30 to agent_alpha
```

### Comprehensive Rollout Test

```bash
# Run all example rollouts
p2engine rollout start config/demo_rollout.yml
p2engine rollout start config/rollout_task_with_payment.yml
p2engine rollout start config/rollout_competitive_payment.yml
p2engine rollout start config/rollout_hierarchical_distribution.yml

# Check results
p2engine ledger overview
p2engine ledger audit
```

## 📚 Key Concepts

### Interaction Stack

Each agent maintains a stack of interaction states (messages, tool calls, results) that can be branched and rewound.

### Effects System

Actions that modify external state (tool calls, delegations) are managed through an effects system with proper isolation and retry logic.

### Artifact Bus

All significant events and data are stored as artifacts with full provenance tracking.

### Deduplication Policies

- **none**: No deduplication
- **penalty**: Track duplicates but allow execution
- **strict**: Block duplicate side-effect operations

## 🔍 Troubleshooting

### Canton Connection Issues

```bash
# Check Canton health
./scripts/canton-health-check.sh

# Debug ledger connection
p2engine ledger debug

# Restart Canton services
pkill -f canton
./scripts/start_canton.sh
```

### Redis Connection

```bash
# Check Redis
redis-cli ping

# Clear Redis (development only!)
redis-cli FLUSHDB
```

### View Logs

```bash
# Main log
tail -f logs/main.log

# Celery worker logs
tail -f logs/run_*/workers/*.log

# Canton logs
tail -f logs/canton/*.log
```

## 📄 Access & Rights

**This is a closed academic work for a Master's thesis.**

- **Access Period**: Sensors (examiners) may view and test the code only during the official examination period
- **Restrictions**: After the examination period, all access must be revoked
- **Intellectual Property**: The ideas, concepts, and implementations in this work may not be reshared or redistributed
- **Authorized Users**: Limited to the thesis supervisor, student, and designated sensors/examiners

## 🛠️ Technology Stack

### Core Framework

- **[LiteLLM](https://github.com/BerriAI/litellm)** - Unified interface for multiple LLM providers
- **[Celery](https://docs.celeryproject.org/)** - Distributed task queue for scalable execution
- **[Redis](https://redis.io/)** - In-memory data store for caching and message passing

### Ledger Technology

- **[Canton](https://www.digitalasset.com/developers)** - Distributed ledger infrastructure
- **[Daml](https://daml.com/)** - Smart contract language for ledger transactions

### Development Tools

- **[Poetry](https://python-poetry.org/)** - Dependency management and packaging
- **[Typer](https://typer.tiangolo.com/)** - CLI interface framework
- **[Rich](https://github.com/Textualize/rich)** - Terminal formatting and UI components
- **[Pydantic](https://pydantic-docs.helpmanual.io/)** - Data validation and settings management

### AI/ML Infrastructure

- **[OpenAI API](https://openai.com/api/)** - Primary LLM provider
- **[Jinja2](https://jinja.palletsprojects.com/)** - Template engine for prompt engineering
- **[JSONSchema](https://json-schema.org/)** - Tool parameter validation

---

<div align="center">
<strong>Master's Thesis Project</strong><br>
<em>Autonomous Systems via Multi-Agent Coordination and Verifiable Infrastructure</em><br>
<br>
© 2025 - Academic Use Only
</div>
