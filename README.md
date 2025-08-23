<!-- Hero -->

What could P2Engine become, a test-bed for collective game theory monetry incetives cot style system at global level reasonging allignemt

Lets have that P2 Logo on top of here

<h1 align="center">P2Engine — Multi-Agent System (WIP)</h1>
<p align="center">
  Orchestrate many AI agents with <i>observable</i> workflows, <i>adaptive</i> evaluation loops, and an <i>auditable</i> trail.
</p>

<p align="center">
  <a href="https://img.shields.io/badge/status-WIP-orange"> <img src="https://img.shields.io/badge/status-WIP-orange" alt="Status: WIP"> </a>
  <a href="https://img.shields.io/badge/framework-Exploratory-blueviolet"> <img src="https://img.shields.io/badge/framework-Exploratory-blueviolet" alt="Framework: Exploratory"> </a>
  <a href="https://img.shields.io/badge/license-Academic-lightgrey"> <img src="https://img.shields.io/badge/license-Academic-lightgrey" alt="License: Academic"> </a>
  <a href="https://img.shields.io/badge/python-3.11%2B-informational"> <img src="https://img.shields.io/badge/python-3.11%2B-informational" alt="Python 3.11+"> </a>
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

P2Engine explores how multiple AI agents can coordinate, critique, and improve each other in open-ended tasks. You can think of it as a <em>framework</em> for multi-agent systems—but we’re still letting it find its final form. This repo is actively evolving and remains a work-in-progress.

P2Engine focuses on four pillars: **orchestration**, **observability**, **adaptation**, and **auditability**. Agents collaborate through non-rigid workflows, log everything for inspection, learn via judge/rollout loops, and leave a tamper-evident trail for accountability.

---

## Quicklinks

- **Test it now:** [GitHub Repo](REPO_URL) · Examples in [`demos/`](demos/)
- **Docs (stub):** [`p2engine/README.md`](p2engine/README.md)
- **Contact:** adam.sioud@protonmail.com · surya.b.kathayat@ntnu.no

---

## Primer

[**Test the framework on GitHub**](REPO_URL) — P2Engine is a multi-agent system framework that emerged as the primary artefact of my master’s thesis. This page is a mosaic of that work: we sketch the design, show demos, and point you to what’s most relevant via the contents below. We describe P2Engine’s pillars, provide runnable examples, and will keep expanding this as the project evolves.

### Why it matters

- **Agentic workflows** without rigid pipelines.
- **See what happened** (full runs are observable + auditable).
- **Get better over time** via judge/rollout-driven adaptation loops.

---

## Gallery — Four Validation Scenarios (2×2)

> Placeholders for now. Drop your GIFs/MP4s into `demos/` and update filenames.

**Row 1**

| E1 — Orchestration                                                                      | E2 — Observability                                                                      |
| --------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------- |
| [![E1 Orchestration (placeholder)](demos/placeholder-e1.gif)](demos/placeholder-e1.mp4) | [![E2 Observability (placeholder)](demos/placeholder-e2.gif)](demos/placeholder-e2.mp4) |

**Row 2**

| E3 — Adaptation Loops                                                                | E4 — Audit Layer                                                                       |
| ------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------- |
| [![E3 Adaptation (placeholder)](demos/placeholder-e3.gif)](demos/placeholder-e3.mp4) | [![E4 Auditability (placeholder)](demos/placeholder-e4.gif)](demos/placeholder-e4.mp4) |

---

## Getting Started

> Local dev only for now.

```bash
# 1) Clone
git clone <REPO_URL> && cd p2engine

# 2) Create env & install
python -m venv .venv && source .venv/bin/activate
pip install -U pip wheel
pip install -e .

# 3) Run a demo
python -m demos.e1_orchestration
```
