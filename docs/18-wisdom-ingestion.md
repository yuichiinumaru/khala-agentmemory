# 18-WISDOM-INGESTION.md: The Harvest Strategy

**Source**: arXiv Harvest (Dec 2025)
**Objective**: Integrate critical insights from 385+ analyzed papers into KHALA v2.1.
**Focus**: Security, Memory Hierarchy, and Agentic Reasoning.

---

## 1. 🛡️ Security Hardening (Priority: Critical)

**Insight**: "GhostEI-Bench" and "Attention is All You Need to Defend Against Indirect Prompt Injection" reveal that VLM and LLM agents are highly susceptible to environmental injection and indirect prompt injection.
**Strategy**: Move beyond simple prompt filtering.
**Action Plan**:
1.  **Implement Visual Guardrails**: For multimodal inputs, implement a "Visual Sanitizer" layer (inspired by GhostEI) that checks for adversarial overlays before processing by the VLM.
2.  **Attention-Based Defense**: Integrate an "Attention Monitor" in `GeminiClient` to detect when the model pays excessive attention to irrelevant or suspicious context blocks (as suggested by the "Attention is All You Need" defense paper).
3.  **Validation**: Create a `tests/security/test_injection.py` suite using examples from GhostEI-Bench.

## 2. 🧠 Memory Architecture Evolution

**Insight**: "O-Mem: Omni Memory System" and "General Agentic Memory Via Deep Research" propose hierarchical, dynamic memory systems that outperform static RAG.
**Strategy**: Refactor `khala/domain/memory` to support "Liquid Hierarchies".
**Action Plan**:
1.  **Dynamic Consolidation**: Move from fixed consolidation intervals to an "Entropy-Based" consolidation trigger (inspired by O-Mem).
2.  **Memory Decay**: Implement "Relevance Decay" where unused memories fade but can be "resurrected" by strong associative cues.
3.  **Graph Integration**: Ensure every memory node in SurrealDB has a `links` edge to related concepts, forming a true knowledge graph.

## 3. 🤖 Reasoning & Reflection (ReflexGrad)

**Insight**: "ReflexGrad" and "Reason-Plan-ReAct" demonstrate that agents with explicit self-reflection loops significantly outperform one-shot agents.
**Strategy**: Institutionalize the "Critic" role.
**Action Plan**:
1.  **The Critic Agent**: Create a dedicated `CriticService` that reviews the output of the `PlanningService` *before* execution.
2.  **Reflection Loop**: Implement a `while not satisfied:` loop in `CLISubagentExecutor` that allows the agent to retry tasks with "Self-Correction" prompts.

## 4. 🚀 Implementation Roadmap

| Phase | Task | Source Paper | Complexity |
| :--- | :--- | :--- | :--- |
| **1. Immediate** | Add Injection Tests | GhostEI-Bench | Medium |
| **1. Immediate** | Enable Reflection Loop | ReflexGrad | Low |
| **2. Tactical** | Entropy-Based Consolidation | O-Mem | High |
| **3. Strategic** | Visual Guardrails | GhostEI-Bench | High |

---

## 5. Wisdom Archive
For full details on the 385 analyzed papers, see:
- `docs/17-deep-research-harvest-consolidated.md`
- `docs/arcticles/*.md`
