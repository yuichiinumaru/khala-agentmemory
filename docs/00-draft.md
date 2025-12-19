# KHALA MASTER DRAFT (00-draft.md)

## 1. Project Character & Sophistication
Khala is a research-heavy platform implementing 170+ cognitive protocols. It treats memory as a multi-modal, multi-tier, and multi-relational graph. It is the "Psychic Link" of the VIVI OS.

## 2. Research Audit Findings (2025-12-19)
- **DDD Implementation**: 4-layer architecture (Domain, Application, Infrastructure, Interface).
- **SurrealDB Mastery**: Advanced schema utilizing HNSW, computed fields, and `fn::decay_score`.
- **Unique Capabilities**: `DreamService` (Memory synthesis) and `HypothesisService` (AI scientific method).

## 3. Identified Critical Gaps
- **Placeholder Implementation**: `KHALAMemoryProvider.process_memory_entities` is disconnected from NER services.
- **Documentation Fragmentation**: Information is scattered across 500+ files and redundant reports.
- **Service Proliferation**: Risk of maintenance burden with 170+ protocols.

## 4. Problem to Solve
How to scale a biological-inspired memory system for multiple agents while maintaining deterministic flow execution and high-fidelity search?

## 5. Decision Matrix (Forge v2.2)
- **Methodology**: Forge (RDD/DDD/TDD/CDD).
- **Core Stacks**: Python (Agno), TypeScript (Dashboard), SurrealDB (Graph-Vector Kernal).
