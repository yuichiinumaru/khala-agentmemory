# 02-TASKS-IMPLEMENTATION.md: Implementation Task List

**Project**: KHALA (Agno + SurrealDB)
**Status**: IN PROGRESS

---

## Progress Tracking

**Total Tasks**: 82 (Primary + Advanced)
**Completed**: 71
**Pending**: 11
**Progress**: 86%

**Project-Wide Completion**:
- **Total Modules**: 13
- **Implemented Modules**: 10 (Modules 1-10)
- **Pending Modules**: 3 (Modules 11-13)

---

## Pending Tasks (Priority)

### Phase 2: Optimization & Novelty (Modules 11 & 12)

#### Phase 2.1: SurrealDB Schema & Logic Optimizations (Module 11)
- [ ] **M11.A.3**: **Graph Model Enhancements** (Strategies 68-77).

#### Phase 2.2: Advanced Search & Time (Module 11)
- [ ] **M11.B.1**: **Full-Text Search Enhancements** (Strategies 93-102).
- [ ] **M11.B.2**: **Time-Series & Geospatial** (Strategies 103-115).

#### Phase 2.3: Experimental Architectures (Module 12)
- [ ] **M12.C.1**: **Agent Cognitive Patterns** (Strategies 116-128).
- [ ] **M12.C.2**: **Advanced Learning & Adaptation** (Strategies 129-140).
- [ ] **M12.C.3**: **Meta-Cognition & Self-Correction** (Strategies 141-159).

### Phase 3: Advanced Intelligence & Reasoning (Module 13)

*Based on 2024-2025 Research Papers: ARM, PromptWizard, LatentMAS, LGKGR, MarsRL.*

#### 13.1 Foundation Layer (Prompt & Reasoning)
- [ ] **13.1.1** Implement **PromptWizard Service** (Strategy 160).
    - Create `PromptOptimizationService` using Genetic Algorithms.
    - Create `prompt_candidates` and `prompt_evaluations` tables in SurrealDB.
    - Integrate LLM feedback loop for prompt mutation.
- [ ] **13.1.2** Implement **ARM (Agentic Reasoning Modules)** (Strategy 161).
    - Define `ReasoningModule` value object/entity.
    - Create `reasoning_modules` table in SurrealDB.
    - Implement module discovery logic (tree search over code space).
    - Update `AgnoAgent` to load homogeneous modules dynamically.

#### 13.2 Knowledge Layer (Graph Reasoning)
- [ ] **13.2.1** Implement **LGKGR Service** (Strategy 162).
    - Create `KnowledgeGraphReasoningService`.
    - Implement 3-phase reasoning: Path Search (Vector) -> Pruning (Heuristic/GNN) -> Evaluation (LLM).
    - Store reasoning traces in `reasoning_paths` table.
- [ ] **13.2.2** Implement **GraphToken Injection** (Strategy 163).
    - Create `GraphTokenService` to fetch KG embeddings.
    - Modify `ContextAssemblyService` to inject KG tokens into LLM prompt.

#### 13.3 Collaboration Layer (Multi-Agent)
- [ ] **13.3.1** Implement **LatentMAS Infrastructure** (Strategy 164).
    - Update `Team` orchestration to support "latent" mode (sharing embeddings/state).
    - Create `latent_states` vector table in SurrealDB.
    - Implement `LatentMemoryRepository` to store/retrieve agent hidden states.
- [ ] **13.3.2** Implement **Hierarchical Teams (FULORA)** (Strategy 165).
    - Create `HierarchicalTeam` class in `khala/application/coordination`.
    - Implement "High-Level" (Guidance) and "Low-Level" (Action) agent roles.
    - Store guidance hints in `hierarchical_coordination` graph edges.

#### 13.4 Optimization Layer (RL & Validation)
- [ ] **13.4.1** Implement **MarsRL Optimizer** (Strategy 166).
    - [ ] Create `MarsRLOptimizer` service.
    - [ ] Define `Solver`, `Verifier`, `Corrector` roles.
    - [ ] Implement individualized reward calculation logic.
    - [x] Store training curves in `training_curves` time-series table.
- [ ] **13.4.2** Implement **AgentsNet Validator** (Strategy 167).
    - Create benchmark suite for network coordination.
    - Visualize network topology in SurrealDB graph.

---

## Completed Tasks

### Phase 1: Foundation (Modules 1-10)
*(See previous version or archive for detailed list of completed tasks 1.1 to 10.5)*
- **Status**: [COMPLETE]

### Phase 2 Completed Items
- [x] **M11.A.1**: Implement **Nested Document Structures** (Strategies 58-61).
      - Implemented `versions` and `events` arrays in schema and client.
- [x] **M11.A.2**: Implement **Computed Fields & Events** (Strategies 62-65).
      - Implemented `decay_score` computed field and `add_memory_event`.
- [x] **M11.A.4**: **Vector Model Tuning** (Strategies 78-92).
      - Multi-Vector support (visual/code embeddings) implemented (Strategy 78).

### Phase 3 Completed Items
- [x] **13.4.1 (Partial)**: Store training curves in `training_curves` time-series table.

---

**Next Actions**:
1. Start with **Task 13.1.1 (PromptWizard)** as it has high impact and is isolated.
2. Proceed to **13.1.2 (ARM)** to restructure agent capabilities.
