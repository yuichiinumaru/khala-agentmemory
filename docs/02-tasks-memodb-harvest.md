# Task List: Operation Memodb Harvest

## Phase 1: Foundation (Prompting & Utils)

- [x] **1. Implement `PromptString` Utility** (High Impact / Low Effort)
    - [x] Create `tests/unit/domain/prompt/test_prompt_string.py` covering concatenation, role handling, and formatting.
    - [x] Create `khala/domain/prompt/utils.py` and implement `PromptString`, `PromptChain` classes (ported from `prompt-string`).
    - [x] Add `System`, `User`, `Assistant` helper shortcuts.
    - [x] Refactor `PromptOptimizationService` (`khala/application/services/prompt_optimization.py`) to use `PromptString`.

## Phase 2: Reasoning Engine (Cognitive Flow)

- [x] **2. Implement `CognitiveCycleEngine`** (High Impact / High Effort)
    - [x] Create `tests/unit/application/orchestration/test_cognitive_engine.py` verifying DAG execution and event triggering.
    - [x] Create `khala/application/orchestration/cognitive_engine.py`.
    - [x] Port `EventEngineCls` logic from `drive-flow`, renaming to `CognitiveEngine`.
    - [x] Implement `SurrealDBEventBroker` to persist critical events to the database (using `SurrealDBClient`).
    - [x] Integrate with `AuditRepository` for trace logging.

## Phase 3: Planning Upgrade (Iterative Planner)

- [ ] **3. Implement `KhalaPlanner`** (Medium Impact / Medium Effort)
    - [ ] Create `tests/unit/application/services/test_khala_planner.py` testing the loop logic and step parsing.
    - [ ] Create `khala/application/services/planning_utils.py` with `parse_step` logic (regex/json parsing adapted from `nano-manus`).
    - [ ] Refactor `PlanningService` to support iterative execution (Loop: Plan -> Execute -> Refine).
    - [ ] Define `Worker` interface and implement `AgnoToolWorker` adapter.

## Phase 4: Developer Experience (SDK)

- [ ] **4. Implement `KhalaClient` SDK** (Medium Impact / Low Effort)
    - [ ] Create `tests/unit/interface/sdk/test_client.py` mocking HTTP calls.
    - [ ] Create `khala/interface/sdk/__init__.py`.
    - [ ] Create `khala/interface/sdk/client.py` implementing `KhalaClient` class.
    - [ ] Implement `Blob` class for handling image uploads (for Multimodal Gemini).

## Phase 5: Cleanup & Verification

- [ ] **5. Final Verification**
    - [ ] Run full test suite: `pytest tests/unit/domain/prompt tests/unit/application/orchestration tests/unit/application/services tests/unit/interface/sdk`.
    - [ ] Remove `references/` directory (once integration is confirmed complete).
