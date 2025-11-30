# 01-PLAN-OVERVIEW.md: KHALA v2.0 Project Plan

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)
**Version**: 2.0
**Framework**: Agno + SurrealDB
**Date**: November 2025
**Status**: Planning Complete

---

## 1. Executive Summary

### Project Vision
Build a **production-ready, template-based Agno agent** that serves as the foundation for all future agent development. This agent will integrate **100+ memory optimization strategies** into a single, cohesive system that can be cloned and customized.

### Core Objective
Create one **functional reference agent** ("Khala") with:
- Complete implementation of all strategies.
- Production-grade code quality.
- Comprehensive documentation.
- Reusability as a template.

### Key Deliverables
1.  **Single Template Agent**: Fully functional Agno agent with integrated memory system.
2.  **Documentation Suite**: Complete technical and operational documentation.
3.  **Test Suite**: Comprehensive testing framework.
4.  **Deployment Kit**: Production deployment scripts.

---

## 2. Project Scope

### In Scope (100+ Strategies)
*See [06-strategies-master.md](06-strategies-master.md) for the complete list.*

**Core Implementation (Foundations)**
- Vector Storage (HNSW) & Graph Relationships
- 3-Tier Memory Hierarchy (Working, Short-term, Long-term)
- Hybrid Search (Vector + BM25 + Metadata)
- Multi-Tenancy & RBAC

**Advanced Implementation (Intelligence)**
- Context Assembly & Token Management
- Consolidation, Deduplication (Hash + Semantic) & Decay
- Entity Extraction & Temporal Analysis
- MCP Interface & Multi-Agent Coordination

**Novel Capabilities (Innovation)**
- LLM Cascading & Cost Optimization
- Self-Verification & Multi-Agent Debate
- Multimodal Support (Image/Code/Table) *excluding GPU processing*
- Advanced Reasoning (Mixture of Thought, Hypothesis Testing)

### Out of Scope
- Multiple agent templates (only 1 reference agent).
- Custom UI/UX beyond admin dashboard (UI handled in `Supernova.JS`).
- Mobile applications.
- Federated deployment.
- **GPU processing** (explicitly excluded).

---

## 3. Implementation Strategy

### Methodology
**Agile + DDD (Domain-Driven Design)**

### Module Organization
*   **Module 1: Foundation**: SurrealDB, Schemas, Basic CRUD.
*   **Module 2: Search System**: Hybrid Search, Intent, Caching.
*   **Module 3: Memory Lifecycle**: Tiers, Consolidation, Deduplication.
*   **Module 4: Processing & Analysis**: Entities, Skills, Background Jobs.
*   **Module 5: Integration**: MCP, Multi-Agent, Monitoring.
*   **Module 6: Cost Optimization**: LLM Cascading, Consistency Signals.
*   **Module 7: Quality Assurance**: Verification, Debate, Traceability.
*   **Module 8: Advanced Search**: Scoring, Topics, Patterns.
*   **Module 9: Production Features**: Audit, Distributed, SOPs.
*   **Module 10: Advanced Capabilities**: Multimodal, Reasoning, Dashboards.

---

## 4. Technical Architecture Overview

**Primary Stack**:
- **Agent Framework**: Agno
- **Database**: SurrealDB 2.0+ (Multi-model: Graph + Vector + Document)
- **LLM**: Gemini 2.5 Pro (Smart), Flash (Fast), GPT-4o-mini (Medium)
- **Language**: Python 3.11+

**Layers**:
1.  **Application**: Agno Agent Template.
2.  **Intelligence**: Intent, Debate, Verification.
3.  **Retrieval**: Hybrid Search, Graph Traversal.
4.  **Storage**: SurrealDB (Vectors, Graph, Documents).
5.  **Optimization**: Background Consolidation, Decay.

---

## 5. Success Metrics

| Metric | Target |
| :--- | :--- |
| **Search Latency (p95)** | <100ms |
| **Embedding Speed** | >1000/sec |
| **Precision@5** | >90% |
| **Cache Hit Rate** | >70% |
| **Verification Pass Rate** | >70% |
| **LLM Cost/Memory** | <$0.03 |
| **System Uptime** | >99.95% |

---

## 6. Risk Management

1.  **SurrealDB Performance**: Mitigate with query optimization and distributed setup.
2.  **API Rate Limits**: Mitigate with caching and cascading.
3.  **Memory Complexity**: Mitigate with modular design and rigorous testing.
4.  **Scope Creep**: Mitigate by strictly adhering to the prioritized task list.

---

**Next Steps**: Proceed to **[02-tasks-implementation.md](02-tasks-implementation.md)** to begin execution.
