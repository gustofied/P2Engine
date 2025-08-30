### P2Engine

- [Quick Start](#quick-start)
- [Basic Usage](#basic-usage)
- [Rollouts](#rollouts)
- [Evals](#evals)
- [Agents](#agents-configagentsyml)
- [Tools](#tools)
- [Ledger Operations](#ledger-operations)
- [Branching](#branching)
- [Configuration Overrides](#configuration-overrides)
- [Logs, Checks, Health of The System](#logs-checks-health-of-the-system)
- [Core Modules](#core-modules)

#### Quick Start

##### Prerequisites

Firts let's make sure we have these

- Python 3.9+
- Redis
- Poetry
- Daml SDK (optional, for ledger features)
- OpenAI API keyi8

##### Installation

Then we clone, install the dependencies and set up the environment variables.
There are a lot of options here, but it's the OpenAI KEY that is the key;) here
And if you want ledger on or not.

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

##### Environment Configuration (.env)

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

##### Running the System

The **primary way** to run P2Engine is through the run_proejct script:

```bash
# This single command starts EVERYTHING:
./scripts/run_project.sh
```

##### What run_project.sh does:

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

So yes when the script is ran, we are dropped into the interactive CLI of P2Engine. And it's here we can start playing around.

#### Basic Usage

##### Starting a Chat

```bash
# Start a conversation with an agent
p2engine chat with agent_alpha

# any agent name works
p2engine chat with x

#  Some agents, such as agent_alpha are preconfigured with
#  personas/tools/temperatures etc which you can define in config/agents.yml

# In the chat:
You> Hello! What can you do?
You> Transfer 25 to agent_beta for helping with analysis
You> What's the weather in Paris?
```

##### Delegation, make use of sub-agents

```bash
# Agents can delegate to each other
You> Delegate to agent_helper: What's the weather in Tokyo?
You> If they did well, reward them 20 units
```

##### Some example commands in our P2Engine Shell to try

I recommend to do, help in the CLI, you will get to see all the commands
Then try some out, it will give feedback if done wrong, and how to do
correctly:)

examples of commands

```bash
p2engine▸ help
p2engine▸ agent list
p2engine▸ conversation list
p2engine▸ conversation stack <conversation_name>
p2engine▸ ledger balance agent_alpha
p2engine▸ rollout start config/demo_rollout.yml
```

#### Rollouts

We have rollouts in P2Engine, we can configure teams, agents, variants, the task, what is the eval, the rubric, and who is the judge. P2Engine supports
dynamic swapping, so we could modify or add new rollouts whilst the P2Engine is running.

##### Example Learning Configuration

```yaml
# config/learning_rollout.yml
teams:
  autonomous_team:
    initial_message: "Solve this complex multi-step problem"
    base:
      agent_id: agent_alpha
      model: openai/gpt-4o
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

##### Here are some examples rollouts you could test

```bash
# Run all example rollouts
p2engine rollout start config/demo_rollout.yml
p2engine rollout start config/rollout_task_with_payment.yml
p2engine rollout start config/rollout_competitive_payment.yml
p2engine rollout start config/rollout_hierarchical_distribution.yml

# Check results
# If ledger is on, and rollout has transactions, it's cool to use these, after a run.
p2engine ledger overview
p2engine ledger audit
```

##### Running Rollouts

The best way to run rollouts is with follow flag, and also if you want
a new visual i'm working on do --rerun flag :)

```bash
# Start a rollout
p2engine rollout start config/rollout_joke.yml
p2engine rollout start config/rollout_joke.yml --follow
p2engine rollout start config/rollout_joke.yml --rerun
p2engine rollout start config/rollout_joke.yml --rerun --follow

# View results
p2engine eval top <session_id> --metric score
```

Rollouts is the key thing I would like to improve on and currently has a lot
of potential, as well as rest of P2Engine, but a lot is hidden, not documented and needs that last polish.

#### Evals

P2Engine includes a pretty proper evaluation framework that is configurable:

##### Built-in Evaluators

- P2Engine has a **gpt4_judge**: Can use it for general quality evaluation
- And custom rubrics for specific use cases

##### Creating Custom Evaluators

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

#### Agents (`config/agents.yml`)

Here is how we could configure some agents we want with specific spec:

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

#### Tools

Here's how to create tools:

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

#### Ledger Operations

And yes P2Engine is extended with a full ledger, it uses Canton Network, and DAML as the smart contracting language..

##### Initialize Wallets

```bash
# Initialize all agent wallets with starting balance
p2engine ledger init --balance 100.0
```

##### Check Balances

```bash
# Check specific agent balance
p2engine ledger balance agent_alpha

# Check system metrics
p2engine ledger metrics

# View all wallets
p2engine ledger overview
```

##### Transfer Funds

```bash
# Direct transfer via CLI
p2engine ledger transfer agent_alpha agent_beta 25.0 --reason "Payment for services"

# Or through agent conversation
p2engine chat with agent_alpha
You> Transfer 50 to treasurer for management fees
```

##### Transaction History

```bash
# View agent's transaction history
p2engine ledger history agent_alpha --limit 20

# Audit trail for all ledger events
p2engine ledger audit
```

#### Branching

One cool thing about P2Engine is that it supports branching on our conversations/chats. You can have multiple branches, checkout back and forth, rewind to the state/step you want.

```bash
# View conversation branches
p2engine conversation branches <conversation_name>

# Rewind to a previous state
p2engine conversation rewind <conversation_name> 10 --branch

# Checkout a different branch
p2engine conversation checkout <conversation_name> <branch_id>
```

#### Configuration Overrides

During run we might want to set new personas or tools for an agent, then we can use these commands.

```bash
# Change agent behavior
p2engine config set-behavior <conversation> weather_expert

# Override tools
p2engine config set-tools <conversation> get_weather,delegate,check_balance

# View current overrides
p2engine config show-overrides <conversation>
```

#### Logs, Checks, Health of The System

##### Canton Connection Issues

```bash
# Check Canton health
./scripts/canton-health-check.sh

# Debug ledger connection
p2engine ledger debug

# Restart Canton services
pkill -f canton
./scripts/start_canton.sh
```

##### Redis Connection

```bash
# Check Redis
redis-cli ping

# Clear Redis (development only!)
redis-cli FLUSHDB
```

##### View Logs

```bash
# Main log
tail -f logs/main.log

# Celery worker logs
tail -f logs/run_*/workers/*.log

# Canton logs
tail -f logs/canton/*.log
```

#### Core Modules

Here is what you could expect at the different modules

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

- **[`/services`](./services/README.md)** - Service layer and DI container

  - ServiceContainer for dependency injection
  - Canton/Daml ledger integration
  - Thread-safe service management

- **[`/cli`](./cli/README.md)** - Command-line interface
  - Interactive chat system
  - Configuration management
  - Conversation inspection
  - Rollout execution
