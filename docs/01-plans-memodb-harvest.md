# Plan: Operation Memodb Harvest

**Status:** Draft
**Phase:** 4 (Expansion)
**Owner:** Jules

## 1. Executive Summary
This plan details the integration of high-value components scavenged from the `memodb-io` ecosystem (`nano-manus`, `drive-flow`, `prompt-string`) into the Khala memory system. The objective is to upgrade Khala's planning, reasoning, and developer experience capabilities using a Test-Driven Development (TDD) approach, strictly adhering to the SurrealDB + Agno + Gemini stack.

## 2. Core Objectives
1.  **Prompt Engineering 2.0:** Implement Object-Oriented Prompting (`PromptString`) to sanitize and structure Gemini interactions.
2.  **Cognitive Flow:** Implement an Event-Driven Reasoning Engine (`CognitiveCycleEngine`) based on `drive-flow` to orchestrate agent thought processes.
3.  **Advanced Planning:** Upgrade `PlanningService` to `KhalaPlanner`, incorporating `nano-manus` iterative logic and step parsing.
4.  **Client SDK:** Establish a clean Python SDK foundation (`KhalaClient`) for external interaction.

## 3. Implementation Plan

### 3.1. PromptString Integration (Low Effort, High Impact)
*Goal:* Replace raw string prompts with a composable, safe abstraction.
*   **TDD Step:** Create `tests/unit/domain/prompt/test_prompt_string.py`.
*   **Implementation:**
    *   Port `prompt-string` logic to `khala/domain/prompt/utils.py`.
    *   Add `System`, `User`, `Assistant` helper classes.
    *   Integrate into `PromptOptimizationService` as a proof-of-concept.

### 3.2. Cognitive Cycle Engine (High Effort, High Impact)
*Goal:* Create a DAG-based engine for agent reasoning loops.
*   **TDD Step:** Create `tests/unit/application/orchestration/test_cognitive_engine.py`.
    *   Test defining a simple DAG (A -> B -> C).
    *   Test async execution.
*   **Implementation:**
    *   Create `khala/application/orchestration/cognitive_engine.py`.
    *   Adapt `drive-flow`'s `EventEngineCls` logic but strip Redis dependencies.
    *   Implement `SurrealDBEventBroker` to log critical events to SurrealDB `audit_log` via `AuditRepository`.

### 3.3. Khala Planner Upgrade (Medium Effort, High Impact)
*Goal:* Move from "Generate Plan" (One-shot) to "Generate -> Execute -> Verify" (Loop).
*   **TDD Step:** Create `tests/unit/application/services/test_khala_planner.py`.
    *   Test `parse_step` regex against Gemini outputs.
    *   Test `Planner.handle` loop mocking the "Worker" execution.
*   **Implementation:**
    *   Refactor `PlanningService` in `khala/application/services/planning_service.py`.
    *   Import `parse_step` logic from `nano-manus` (adapted).
    *   Define `AgnoWorker` adapter to treat Agno Agents/Tools as "Workers".

### 3.4. Khala SDK Foundation (Medium Effort, Medium Impact)
*Goal:* Provide a clean entry point for developers.
*   **TDD Step:** Create `tests/unit/interface/sdk/test_client.py`.
*   **Implementation:**
    *   Create `khala/interface/sdk/client.py`.
    *   Implement `KhalaClient` and `Blob` (for images).
    *   Ensure it uses `httpx` to call the local FastAPI instance.

## 4. Verification & Validation
*   **Unit Tests:** All new components must reach 90%+ coverage.
*   **Integration Tests:** Verify `KhalaPlanner` successfully creates and executes a multi-step plan using a mock Gemini response and a real SurrealDB instance.

## 5. Pre-Commit Checklist
*   [ ] Run new unit tests.
*   [ ] Verify no regressions in existing services.
*   [ ] Update Architecture documentation.
