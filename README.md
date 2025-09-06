<div align="center">
<h1> P2Engine: A Multi-Agent System Framework</h1>
</div>
<div align="center">
<b> A framework + runtime to build, run, and evaluate multi-agent systems. Extended with the Canton Network to enable monetary incentives, payments, and audits. </b> 
</div>
<br>
<div align="center"> orchestrate agents • evaluate each step • branch & rewind • trajectories & artifacts • replay & observe
</div>

---

The full framework lives inside the [`p2engine/`](p2engine/) directory, with setup instructions and detailed documentation in [`p2engine/README.md`](p2engine/README.md).

I’ve also written an article on P2Engine, the research, the ideas, visions, and more.. [Read it here →](https://www.adamsioud.com/projects/p2engine.html)

[Showcase](#showcase) • [How It Works](#how-it-works) • [Rollouts](#rollouts) • [Ledger](#ledger) • [How It Works (Diagrams)](#how-it-works-diagrams) • [Future](#future)

---

## Showcase

<!-- Centered 2×2 demo gallery that works on GitHub -->
<div align="center">

  <table align="center">
    <tr>
      <td align="center" width="420">
        <a href="https://www.adamsioud.com/projects/p2engine.html?v=e1">
          <img src="demos/thumbs/e1_320x180.gif" alt="Agent Delegation">
        </a><br>
        <sub><b>Agent Delegation</b></sub>
      </td>
      <td align="center" width="420">
        <a href="https://www.adamsioud.com/projects/p2engine.html?v=e2">
          <img src="demos/thumbs/e2_320x180.gif" alt="Branch Rewind">
        </a><br>
        <sub><b>Branch Rewind</b></sub>
      </td>
    </tr>
    <tr>
      <td align="center" width="420">
        <a href="https://www.adamsioud.com/projects/p2engine.html?v=e3">
          <img src="demos/thumbs/e3_320x180.gif" alt="Rollouts">
        </a><br>
        <sub><b>Rollouts</b></sub>
      </td>
      <td align="center" width="420">
        <a href="https://www.adamsioud.com/projects/p2engine.html?v=e4">
          <img src="demos/thumbs/e4_320x180.gif" alt="Ledger">
        </a><br>
        <sub><b>Ledger</b></sub>
      </td>
    </tr>
  </table>
<p><em>Click any demo for a full video demonstration</em></p>
</div>

**Agent Delegation** — Agents delegate tasks to sub-agents. Conversation context is preserved across all agent interactions.

**Branch Rewind** — Rewind conversations to any point and explore alternative paths. Switch between different conversation branches.

**Rollouts** — Run multiple agent configurations simultaneously, A/B testing. Compare performance metrics (artifacts, reward, token usage, costs, ledger transactions, speed, and more) and visualize results in real-time.

**Ledger** — Agents have wallets and can transfer funds. All transactions are recorded with complete audit trails.

---

## How It Works

P2Engine's architecture and internals are inspired by a beautiful and well-thought-out blueprint laid down by [Erik](https://eriksfunhouse.com). His architecture proposal and taste for systems, what is an agent, tools, prompt templates, reasoning etc. have guided P2Engine to what it is today. A big recommendation: check out his series, here is [Part 1](https://eriksfunhouse.com/writings/state_machines_for_multi_agent_part_1/), and then continue to [Part 2](https://eriksfunhouse.com/writings/state_machines_for_multi_agent_part_2/), [Part 3](https://eriksfunhouse.com/writings/state_machines_for_multi_agent_part_3/), and [Part 4](https://eriksfunhouse.com/writings/state_machines_for_multi_agent_part_4/).

P2Engine’s orchestration is fundamentally built on finite state machine (FSM) principles, where each agent conversation progresses through well-defined states with explicit transition rules.

It runs LLM-agents in discrete steps. Each step produces artifacts, and a separate and async evaluator scores them. You can think of it like this: the agent thinks, acts, and creates something; the evaluator observes, scores.

**Finite State Machine**

Each agent conversation moves through well-defined states: UserMessage → AssistantMessage or ToolCall → ToolResult → AssistantMessage, with WaitingState managing async operations. Agent delegation adds AgentCall/AgentResult states, and conversations end with FinishedState. This explicit state management makes it easier to create reliable coordination and to debug the systems.

**Interaction Stack**

Every agent maintains a stack storing complete interaction history. This enables conversation rewinding, branch creation for alternative paths, and preserved context across agent handoffs.

**Effect-Based Execution**

Agent decisions generate "effects" (tool calls, payments, delegations) that execute asynchronously via Celery workers.

**Artifact Evaluation**

Every agent action produces artifacts that evaluators score automatically.

**Ledger**

Canton/DAML ledger integration provides agent wallets, automated payments, and immutable audit trails. Agents can earn rewards for the quality of work they do, with all transactions recorded in immutable audit trails.

---

## Rollouts

<p align="center">
  <a href="https://www.adamsioud.com/projects/p2engine.html?v=hero">
    <img src="demos/rollout_rerun_showcase_4x_short.gif" alt="Rerun Showcase" width="450">
  </a>
  <br>
  <em>Click for a full video demonstration</em>
</p>

_To test how P2Engine was working I used a combination of chat and rollouts. Rollouts became the primary way to sort of simulate stuff and see the interactions, debug/inspect the logs, and inspect the transactions happening on the ledger. This means in its current form, it's a bit sided to facilitate more of experimental cases and this is reflected in the current configuration files (e.g., [rollout_joke.yml](p2engine/config/rollout_joke.yml)). They are more examples of simulations rather than true A/B tests._

**But the infrastructure does supports proper rollouts**

The rollout system provides A/B testing capabilities for systematically comparing agent configurations, tool combinations, and parameters. Built in the [runtime/rollout/](p2engine/runtime/rollout/) module with Celery integration, it enables a simple distributed execution and parallel evaluation of multiple variants.

**How It Works**

Create YAML configuration files that specify teams, base settings, and variants. The system expands these into individual experiments, runs them in parallel using Celery workers, and collects the metrics such as they are conversation artifacts, rewards, token usage, costs, ledger transactions, speed.

**Real-time Monitoring**

We can watch rollouts unfold through the P2Engine CLI with live progress tables, and stream to Rerun viewer for more visual monitoring. Rerun can also be used to replay, rewind and inspect our rollouts. Each variant gets automatic evaluation scores, and the system aggregates results for easy comparison of what works best.

**The Foundation for Learning**

Rollouts is the key infrastructure to enable P2Engine's future learning loop. Currently, evaluators score agent outputs automatically, so the next step is to close the loop and use these scores to automatically propagate successful configurations to underperforming variants, creating a system that improves itself through experimentation. Something like that, there are many ways here, and we will talk about that in the [Future](#future) section.

---

## Ledger

The idea behind the ledger is to introduce monetary incentives, payments, and audits into multi-agent systems and P2Engine does this by integrating Canton/DAML. Agents have wallets, can transfer funds, and earn rewards based on performance. All transactions recorded in immutable audit trails.

**Agent Wallets & Transfers**

Each agent gets a wallet managed by DAML smart contracts that enforce validation rules. Agents can transfer funds to each other, with automatic overdraft protection and complete transaction history.

**Tools**

Agents use standard tools like transfer_funds, check_balance, and reward_agent. The system automatically tracks all financial activity during conversations and rollouts.

**Incentive Alignment**

Through the evaluators in P2Engine, Agents earn rewards for quality work during a rollout.

**Audit Trails**

Every transaction flows through the artifact bus, creating permanent records. Rollouts capture before/after ledger snapshots, enabling cool experiments.

**Why Canton**

Canton provides smart contract validation, privacy-preserving operations, and the robust infrastructure needed for financial accountability in production multi-agent systems.

<br>

---

## How It Works (Diagrams)

Here are four diagrams presenting key aspects of P2Engine's implementation.

#### Execution Sequence

<p align="center">
  <img src="p2engine/docs/architecture/execution-sequence.png" alt="Execution Sequence" width="820">
  <br>
  <em>Execution Sequence Flow</em>
</p>

The system execution follows the sequence shown in our figure here [figure maybe wrong word], demonstrating end-to-end integration across all architectural layers. The execution unfolds through six integrated stages:

- **Agent Processing** — Consumes conversation states and produces responses or tool invocations.
- **Tool Execution** — Runs asynchronously, publishing results back into the conversation streams.
- **State Progression** — Captures every activity as state transitions flowing through the orchestration layer.
- **Event Publication** — Automatically pushes those state changes to the observability layer for real-time monitoring and analysis.
- **Evaluation Triggering** — Fires upon conversation completion or significant milestones, invoking automated quality assessments.
- **Adaptation Feedback** — Uses evaluation results to refine future agent configurations via the adaptation layer.

---

#### Unified Event Stream

<p align="center">
  <img src="p2engine/docs/architecture/observability-events.png" alt="Observability Events" width="820">
  <br>
  <em>Every interaction captured for full traceability</em>
</p>

The observability architecture is built around four core mechanisms:

- **Universal Event Streaming** — Ensures that every system activity flows through a central event stream, making agent decision-making and system-wide behavior patterns fully transparent in real time.
- **Complete Traceability** — Records both metadata and payload in each event, preserving causal links across all agent interactions for a holistic understanding.
- **Real-time Transparency** — Leverages live event streams to power operational monitoring and debugging interfaces, keeping the system observable during execution.
- **Event Logs** — Captures events exhaustively for post-hoc examination of agent behaviors and system performance.

---

#### FSM

<p align="center">
  <img src="p2engine/docs/architecture/orchestration-fsm.png" alt="Orchestration FSM" width="820">
  <br>
  <em>Finite State Machine Flow</em>
</p>

P2Engine implements finite state machine orchestration, ensuring coherent state progression while enabling dynamic routing decisions and handling non-deterministic outputs from agents.

The design rests on four interlocking ideas, fully inspired by Erik’s work.

- **Emergent Coordination** — Empowers the system to decide at runtime how many agents to deploy and how to assign tasks, moving beyond rigid sequential workflows to truly configurable behavior.
- **Finite State Machine Control** — Governs state transitions with explicit rules and handlers, ensuring deterministic progression while allowing dynamic routing based on agent outputs.
- **Conversation Branching** — Allows interaction histories to fork at any point, supporting experimental workflows and comparative analyses of different coordination strategies.
- **Dynamic Agent Delegation** — Enables agents to spawn sub-agents and sub-conversations, creating a hierarchical task decomposition that emerges from actual system needs rather than a predetermined plan.

---

#### Transaction Flow

<p align="center">
  <img src="p2engine/docs/architecture/transaction_flow.png" alt="Transaction Flow" width="820">
  <br>
  <em>It shows the From initiation to ledger confirmation</em>
</p>

The transaction flow ensures that all financial operations follow a consistent pattern with proper validation, execution, and recording. Our image illustrates the complete flow from initiation to ledger confirmation. And this it how it goes, every balance change and transfer (Canton/DAML) is appended to an immutable trail with the relevant metadata. This supports post-hoc inspection, compliance reporting, and reconciliation, while keeping operational paths simple and verifiable. [could we have a sentence like this or no no?]

---

## Future

So, what’s next for P2Engine?

A first big win is to **close the learning loop.** Use the stored trajectories and evaluator rewards to optimize system prompts, routing, tools, and model choices. The initial focus will be "System Prompt Learning" where the goal will be to improve the “program around the model” (prompts, tool availability, temperatures, routing) instead of retraining weights. And I do think this type of learning that fits nicely with P2Engine, and is not a long way away to achieve. We need to first firm up the rollout module, evaluator, and rewards, fix a few internals, then already we can start experimenting with this learning loop.

In the system prompt learning loop, the router/root agent gives several sub-agents the same task with different configs, scores their steps/outputs, and propagates the best strategy (prompt text, tool allowlist, model, temperature) to weaker variants. Updates can be applied per-step, at checkpoints, or at the end of the trajectory. We treat each system prompt as a configuration to optimize. It learns which of the prompts models to adjust what works which approaches worked etc. So as Karpathy says its about figuring out which approach for an agent is the best, and that is often steered by the system prompt itself not the weights.

So again, treat each system prompt as a living program the root/router edits based on evaluator feedback. During a rollout, the router compares sibling agents (same task, different configs), propagates the best-performing strategies (prompt text, tool choices, temperature), and normalizes around them.

This idea adopts, reflects and builds upon the thinking of:

- [A tweet by Karpathy on System Prompt Learning](https://x.com/karpathy/status/1921368644069765486)
- [Against RL: The Case for System 2 Learning](https://blog.elicit.com/system-2-learning)
- [Part 4: Improving agent reasoning](https://www.arnovich.com/writings/state_machines_for_multi_agent_part_4/), and [More Thoughts on Agents](https://www.arnovich.com/writings/more_on_agents/)

Once that’s in place, who knows where P2Engine goes next!
