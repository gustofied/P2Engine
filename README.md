<!-- Hero -->

<h1 align="center">P2Engine: A Multi-Agent System Framework</h1>

<p align="center"><strong>
A framework + runtime to build, run, and evaluate multi-agent systems. Extended with the Canton Network to enable monetary incentives, payments, and audits.
</strong></p>

<p align="center">
  Orchestrate many AI agents with <i>observable</i> workflows, 
  <i>adaptive</i> evaluation loops, and an <i>auditable</i> trail.
</p>


<p align="center">
  <a href="#quicklinks">Quick Links</a> •
  <a href="#primer">Primer</a> •
  <a href="#gallery--four-validation-scenarios-22">Gallery</a> •
  <a href="#getting-started">Getting Started</a> •
  <a href="#roadmap">Roadmap</a> •
  <a href="#research--publication">Research</a>
</p>

---

P2Engine explores how multiple AI agents can coordinate, critique, and improve each other in open-ended tasks.  
Think of it as a <em>framework</em> for multi-agent systems — but still evolving and work-in-progress.

The framework emphasizes four pillars: **orchestration**, **observability**, **adaptation**, and **auditability**.  
Agents collaborate through flexible workflows, log everything for inspection, learn via judge/rollout loops, and leave a tamper-evident trail for accountability. A DAML/Canton ledger integration enables balances, transfers, rewards, and an auditable payment trail between agents.

---

## Quicklinks

- **Test it now:** [GitHub Repo](REPO_URL) · Examples in [`demos/`](demos/)
- **Docs (stubs):** [`docs/`](docs/)
- **Ledger guide:** [`ledger.md`](ledger.md)
- **Contact:** adam.sioud@protonmail.com · surya.b.kathayat@ntnu.no

---

## Primer

[**Test the framework on GitHub**](REPO_URL) —  
P2Engine is a framework + runtime for multi-agent orchestration. Wire up LLM, rule-based, and human-in-loop agents; execute conversations through an auditable interaction stack; capture tool calls and results as artifacts; run judge/eval rollouts; and (optionally) settle incentives on a Canton ledger.

### Why it matters

- **Agentic workflows** without rigid pipelines.  
- **Transparency** — full runs are observable and auditable.  
- **Self-improvement** via judge/rollout-driven adaptation loops.  
- **Incentives** — balances, transfers, and rewards via Canton.

---

## Gallery — Four Validation Scenarios (2×2)

> Temporary: all cells use `demos/banner.gif` for consistent feel.

<div align="center">

| E1 — Orchestration                                                                 | E2 — Observability                                                                 |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| <div align="center"><img src="demos/banner.gif" alt="E1 Orchestration" width="320"></div> | <div align="center"><img src="demos/banner.gif" alt="E2 Observability" width="320"></div> |

| E3 — Adaptation Loops                                                              | E4 — Audit Layer                                                                   |
| ---------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------- |
| <div align="center"><img src="demos/banner.gif" alt="E3 Adaptation Loops" width="320"></div> | <div align="center"><img src="demos/banner.gif" alt="E4 Audit Layer" width="320"></div> |

</div>

---

## Getting Started

> Local development only for now.

```bash
# 1) Clone
git clone <REPO_URL> && cd p2engine

# 2) Create env & install
python -m venv .venv && source .venv/bin/activate
pip install -U pip wheel
pip install -e .

# 3) Run a demo
python -m demos.e1_orchestration
