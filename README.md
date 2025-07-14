# P2Engine: A Multi-Agent System Framework

**Master's Thesis**  
*Adam Dybwad Sioud*  
*Supervisor: Surya Kathaya*  
*NTNU – Norges teknisk-naturvitenskapelige universitet, Department of Computer Science*   
*2025*

## Contact
*adam.sioud@protonmail.com*  
*surya.b.kathayat@ntnu.no*  

## Abstract

This thesis presents **P2Engine**, a framework for autonomous multi-agent systems built on four foundational pillars: **orchestration**, **observability**, **adaptation**, and **auditability**. The system demonstrates how multiple agents can coordinate dynamically through emergent, non-rigid workflows while maintaining comprehensive audit layers and enabling continuous adaptation through monetary incentives and adaptation loops.

## Core Contributions

1. **Multi-Agent System Framework**: Observable architecture with comprehensive logging and configurable agent coordination enabling truly agentic behavior
2. **Audit Layer Integration**: Distributed ledger-based verification enabling monetary incentives, accountability, and tamper-evident records
3. **Adaptation Infrastructure**: Judge-based evaluation with rollout engine supporting adaptation loops and future adaptation methods integration
4. **Empirical Validation**: Demonstrated effectiveness across our four evaluation criteria (E1-E4) through controlled rollout simulations

## Repository Structure

```
.
├── p2engine/          # Core framework implementation
├── diagrams/          # Architecture and flow diagrams  
├── thesis/            # LaTeX source files
├── demos/             # Video demonstrations of E1-E4 validation scenarios
```

## Quick Start

**P2Engine** realizes truly agentic systems through our four pillars:

- **Orchestration**: Dynamic task decomposition and agent coordination without rigid workflows, enabling emergent and intelligent behavior
- **Observability**: Complete visibility into system states and agent interactions for real-time understanding, debugging, and system adjustment
- **Adaptation**: Structured adaptation loops converting operational experience into improved configurations at both system and agent levels
- **Auditability**: Tamper-evident records enabling monetary incentives, regulatory compliance, and comprehensive accountability

For implementation details, see [`p2engine/README.md`](p2engine/README.md).

## Validation Results

The framework was validated through four systematic evaluation criteria:

- **E1 (Orchestration Correctness)**: Verified state transition compliance and deterministic replay capabilities
- **E2 (Audit Layer Integrity)**: Confirmed comprehensive transaction mapping and cryptographic verification  
- **E3 (Adaptation Efficacy)**: Validated reward-evaluation correlation and adaptation loop foundations
- **E4 (Configurability)**: Demonstrated component integration via configuration-only modifications

Video demonstrations of each validation scenario are available in [`demos/`](demos/).

## Key Results

The framework addresses the fundamental challenge of creating truly autonomous systems that can:

1. **Coordinate Intelligently**: Non-rigid orchestration enabling emergent, agentic behavior rather than sequential workflows
2. **Remain Observable**: Complete system transparency enabling real-time adjustment, debugging, and understanding
3. **Adapt Continuously**: Systematic feedback through adaptation loops and monetary incentives for continuous improvement
4. **Maintain Accountability**: Comprehensive audit layers supporting compliance, verification, and economic incentives

Empirical validation through rollout simulations demonstrates:
- Dynamic agent collaboration with configurable task decomposition
- Complete observability through comprehensive logging and state tracking
- Automated reward distribution based on judge-based performance evaluation
- Successful integration of new agents and adaptation methods through configuration alone

## Future Directions

- Complete adaptation loop implementation with reinforcement learning and other adaptation methods
- Advanced orchestration patterns enabling more sophisticated emergent behaviors
- Scalable deployment across institutional settings with enhanced regulatory compliance
- Cross-system agent interoperability for larger autonomous ecosystems

## Access & Rights

This is a closed academic work. Code access restricted to:
- Thesis supervisor
- Student author  
- Designated examiners (evaluation period only)

**Note**: Ideas and implementations require explicit permission for redistribution.

---

© 2025 - Academic Use Only
