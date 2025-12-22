# KHALA STRATEGIC PLAN (01-plan.md)

## Vision
Khala provides a high-fidelity, cognitive memory kernel for VIVI OS agents, enabling shared consciousness through hierarchical, multi-modal storage and reasoning.

## Strategic Domains
Detailed technical plans are organized by domain to maintain granularity without context overflow.

### 1. [UI/UX & Visualization](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/01-plans/ui-ux.md)
- **Goal**: Real-time visualization of memory graphs and agent entropy.
- **Key Component**: Khala Console (React/Vite).

### 2. [Memory Architecture (MemoDB)](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/01-plans/memodb.md)
- **Goal**: 3-Tier hierarchy (Tier 1: Hot/Cache, Tier 2: Warm/SurrealDB, Tier 3: Cold/Archived).
- **Process**: Automated promotion and consolidation.

### 3. [Infrastructure Layer (SurrealDB)](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/01-plans/surrealdb.md)
- **Goal**: Maximize SurrealDB v2.0 capabilities (HNSW indices, live queries).
- **Integration**: Surrealist setup and schema optimization.

### 4. [Technical Debt & Optimization](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/01-plans/technical-debt.md)
- **Goal**: Resolve implementation gaps (e.g., entity extraction placeholder) and fragmentation.
- **Audit Findings**: High entropy detected in legacy docs; Forge refactor is the mitigation.

### 5. [Research & Future Integration](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/01-plans/arc-prize.md)
- **Goal**: Incorporate ARC Prize strategies and novel cognitive protocols (MoT, PoE).

---

## Technical Constraints
- **Model Hierarchy**: `gemini-3-pro-preview` for reasoning, `gemini-3-flash-preview` for routine tasks.
- **Database**: SurrealDB v2.0+ is mandatory.
- **Protocol**: All operations must be asynchronous and TDD-backed.
