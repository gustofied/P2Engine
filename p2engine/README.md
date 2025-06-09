# P2Engine - Multi-Agent Orchestration Framework

<div align="center">

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![Poetry](https://img.shields.io/badge/dependency%20management-poetry-blueviolet)](https://python-poetry.org/)
[![Redis](https://img.shields.io/badge/cache-redis-red)](https://redis.io/)
[![Celery](https://img.shields.io/badge/task%20queue-celery-green)](https://docs.celeryproject.org/)
[![Daml](https://img.shields.io/badge/ledger-daml-blue)](https://www.digitalasset.com/developers)

_A production-ready framework for orchestrating conversational AI agents with distributed task execution, financial ledger integration, and comprehensive evaluation capabilities._

</div>

## 🌟 Overview

P2Engine is a sophisticated multi-agent orchestration platform that enables:

- **Multi-Agent Conversations**: Agents can delegate tasks to each other, creating complex interaction hierarchies
- **Financial Ledger Integration**: Built-in Canton/Daml ledger for agent wallet management and transactions
- **Distributed Task Processing**: Celery-based task queue for scalable tool execution
- **Evaluation Framework**: Automated quality assessment with configurable judges and metrics
- **Rollout System**: A/B testing and variant comparison for agent configurations
- **Tool Ecosystem**: Extensible tool system with caching, deduplication, and post-effects

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                           │
├─────────────────────────────────────────────────────────────────┤
│                         Runtime Engine                          │
├──────────────┬─────────────┬──────────────┬────────────────────-┤
│   Agents     │   Tools     │  Orchestrator│   Evaluations       │
├──────────────┴─────────────┴──────────────┴────────────────────-┤
│                      Infrastructure Layer                       │
├────────────────────────┬────────────────────────────────────────┤
│   Redis    │  Celery   │   Canton/Daml   │   Artifact Bus       │
└────────────────────────┴────────────────────────────────────────┘
```

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
# Edit .env and add your OPENAI_API_KEY

# Initialize Canton/Daml (optional, for ledger features)
./scripts/setup_canton.sh
```

### Running the System

```bash
# Start everything with the run script
./scripts/run_project.sh

# Or start components manually:
# 1. Start Redis
redis-server

# 2. Start Canton (if using ledger features)
./scripts/start_canton.sh

# 3. Start Celery workers
poetry run celery -A runtime.tasks.celery_app worker -Q ticks -n ticks@%h
poetry run celery -A runtime.tasks.celery_app worker -Q tools -n tools@%h
poetry run celery -A runtime.tasks.celery_app worker -Q evals -n evals@%h
poetry run celery -A runtime.tasks.celery_app worker -Q rollouts -n rollouts@%h

# 4. Start the engine
poetry run python runtime/engine.py

# 5. Launch CLI
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

## 🧪 Rollout System

The rollout system enables A/B testing and evaluation of different agent configurations:

### Example Rollout Configuration

```yaml
# config/example_rollout.yml
teams:
  weather_team:
    initial_message: "What's the weather in major cities?"
    base:
      agent_id: agent_alpha
      model: openai/gpt-4o
    variants:
      - tools: ["get_weather"]
        temperature: 0.3
      - tools: ["get_weather", "delegate"]
        temperature: 0.7
    eval:
      evaluator_id: gpt4_judge
      metric: score
      rubric: |
        Score based on:
        - Accuracy of weather information (0.5)
        - Helpfulness and clarity (0.5)
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

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [LiteLLM](https://github.com/BerriAI/litellm) for LLM provider abstraction
- Uses [Canton](https://www.digitalasset.com/developers) for distributed ledger functionality
- Powered by [Celery](https://docs.celeryproject.org/) for distributed task processing
- UI components from [Rich](https://github.com/Textualize/rich) and [Typer](https://typer.tiangolo.com/)

---

<div align="center">
Built with ❤️ for the future of multi-agent AI systems
</div>
