# KHALA v2.1 - MASTER TASK LIST

**Status**: Active
**Focus**: Resurrection & Evolution
**Stack**: Agno + SurrealDB + Gemini (Strict)

---

## 🏗️ PHASE 1: CRITICAL STABILIZATION (Agno/Gemini/Surreal)
*Objective: Ensure the system is secure, reliable, and uses the correct infrastructure.*

### 1.1. Self-Verification Gate
- [x] **Task**: Enforce quality control on memory ingestion.
    - [x] **Subtask**: Integrate `VerificationGate.verify_memory()` into `MemoryLifecycleService.ingest_memory`.
    - [x] **Subtask**: Define rejection logic (e.g., if Score < 0.7, route to `trash_can` table).
    - [x] **Subtask**: Add unit tests for rejection scenarios.

### 1.2. Intent Classification (Gemini)
- [x] **Task**: Enable smart routing for search.
    - [x] **Subtask**: Refactor `HybridSearchService` to default `auto_detect_intent=True`.
    - [x] **Subtask**: Enhance `IntentClassifier` to support `Fact` vs `Concept` vs `Meta` intents.
    - [x] **Subtask**: Update routing logic: `Fact` -> BM25, `Concept` -> Vector.

### 1.3. Model Registry (Codebase)
- [x] **Task**: Eliminate hardcoded model strings.
    - [x] **Subtask**: Create `khala/infrastructure/gemini/models.py` (Registry).
    - [x] **Subtask**: Define constants: `GEMINI_PRO`, `GEMINI_FLASH`, `EMBEDDING_V1`.
    - [x] **Subtask**: Grep and replace all string literals in `khala/` with registry constants.

### 1.4. Distributed Consolidation (Surreal/Async)
- [ ] **Task**: Move consolidation out of the request loop.
    - [ ] **Subtask**: Implement `JobRepository` in SurrealDB (Table `jobs`).
    - [ ] **Subtask**: Create `ConsolidationWorker` (Agno Agent) that polls `jobs`.
    - [ ] **Subtask**: Update `MemoryLifecycleService` to enqueue jobs instead of `await`.

---

## 🚀 PHASE 2: CORE ENHANCEMENTS (Memodb Harvest)
*Objective: Upgrade the Cognitive Engine and Planner.*

### 2.1. PromptString Implementation
- [x] **Task**: Object-Oriented Prompting.
    - [x] **Subtask**: Port `PromptString` class to `khala/domain/prompt/`.
    - [x] **Subtask**: Implement `User`, `System`, `Assistant` wrappers.
    - [x] **Subtask**: Refactor `PromptOptimizationService` to use the new class.

### 2.2. Cognitive Cycle Engine
- [x] **Task**: Event-Driven Reasoning DAG.
    - [x] **Subtask**: Create `khala/application/orchestration/cognitive_engine.py`.
    - [x] **Subtask**: Implement `CognitiveEngine` class (Adapter of `drive-flow`).
    - [x] **Subtask**: Implement `SurrealDBEventBroker` for persistence.
    - [x] **Subtask**: Create DAG for "Standard RAG" (Search -> Reason -> Answer).

### 2.3. Khala Planner (Iterative)
- [x] **Task**: Loop-based planning.
    - [x] **Subtask**: Create `khala/application/services/khala_planner.py`.
    - [x] **Subtask**: Implement `parse_step` logic (Regex for Step/Thought/Action).
    - [x] **Subtask**: Implement `while not done:` loop with max steps.
    - [x] **Subtask**: Integrate `AgnoToolWorker` adapter.

---

## 🧠 PHASE 3: INTELLIGENCE & ADAPTATION (Adaptation/ARC Harvest)
*Objective: Make the system "Think" and "Adapt".*

### 3.1. Self-Challenging Retrieval (Strategy 173)
- [x] **Task**: Verify memories before use.
    - [x] **Subtask**: Create `SelfChallengingService`.
    - [x] **Subtask**: Implement `challenge_memory(query, memory) -> bool` using Gemini.
    - [ ] **Subtask**: Integrate into `HybridSearchService`.

### 3.2. Adaptive Query Router (Strategy 172)
- [x] **Task**: Route based on complexity.
    - [x] **Subtask**: Implement `QueryRouter` agent (Gemini Flash).
    - [ ] **Subtask**: Define routing table (Fact/Concept/Reasoning).
    - [ ] **Subtask**: Integrate into `CognitiveEngine`.

### 3.3. Adaptive Graph Evolution (Strategy 171)
- [ ] **Task**: Heal the graph structure.
    - [ ] **Subtask**: Implement `IndexRepairService.detect_orphans()`.
    - [ ] **Subtask**: Create `GraphArchitect` agent to link unconnected nodes.

### 3.4. Feedback-Driven Search Tuning (Strategy 174)
- [ ] **Task**: Optimize parameters.
    - [ ] **Subtask**: Implement `AdaptiveSearchTuner`.
    - [ ] **Subtask**: Log search success/failure.
    - [ ] **Subtask**: Adjust `alpha` and `top_k` based on feedback.

### 3.5. Refinement Reasoning Loop (Strategy 178 / SOAR)
- [ ] **Task**: Generate-Verify-Refine.
    - [ ] **Subtask**: Create `RefinementReasoningService`.
    - [ ] **Subtask**: Implement `attempt_solve -> verify -> refine` loop.
    - [ ] **Subtask**: Use `VerificationGate` as feedback signal.

### 3.6. Product of Experts (Strategy PoE)
- [ ] **Task**: Consensus-based verification.
    - [ ] **Subtask**: Create `PoEVerifier`.
    - [ ] **Subtask**: Generate 3 perspectives (e.g., Logical, Factual, Contextual).
    - [ ] **Subtask**: Compute Geometric Mean of scores.

---

## 🛡️ PHASE 4: WISDOM HARVEST (Dec 2025)
*Objective: Security and Advanced Memory.*

### 4.1. Visual Injection Defense (Strategy 175)
- [ ] **Task**: Sanitize multimodal inputs.
    - [ ] **Subtask**: Create `VisualSanitizer` in `MultimodalService`.
    - [ ] **Subtask**: Check for text overlays or adversarial patterns.

### 4.2. Attention Monitor (Strategy 176)
- [ ] **Task**: Detect suspicious model focus.
    - [ ] **Subtask**: Hook into Gemini API response metadata.
    - [ ] **Subtask**: Flag responses where attention distribution is highly skewed (if accessible) or use proxy metric (repetitive token output).

### 4.3. Entropy-Based Consolidation (Strategy 177)
- [ ] **Task**: Smart consolidation triggers.
    - [ ] **Subtask**: Implement `calculate_entropy(text)` (Python or WASM).
    - [ ] **Subtask**: Trigger consolidation when `entropy > threshold`.

---

## ⚡ PHASE 5: INFRASTRUCTURE & OPTIMIZATION (Surreal)
*Objective: Leverage the database engine.*

### 5.1. Surrealist Admin Setup
- [ ] **Task**: Enable Admin UI.
    - [ ] **Subtask**: Create `docs/sops/sop-04-surrealist-setup.md`.
    - [ ] **Subtask**: Export `khala_admin.surql` queries.

### 5.2. Surrealism WASM (Strategy 181)
- [ ] **Task**: Offload logic to DB.
    - [ ] **Subtask**: Set up Rust/WASM build chain.
    - [ ] **Subtask**: Implement `entropy.rs`.
    - [ ] **Subtask**: Deploy to SurrealDB and benchmark.

---

## 🔮 PHASE 6: ADVANCED RESEARCH (Titans/MIRAS)
*Objective: Long-term memory evolution.*

### 6.1. Surprise Scoring (Strategy 179)
- [ ] **Task**: Store "Surprise".
    - [ ] **Subtask**: Add `surprise_score` to Memory schema.
    - [ ] **Subtask**: Calculate surprise (Distance from Centroid) on ingestion.

### 6.2. Retention Gates (Strategy 180)
- [ ] **Task**: Dynamic forgetting.
    - [ ] **Subtask**: Implement `retention_weight` decay.
    - [ ] **Subtask**: Create pruning job based on weight.

---
