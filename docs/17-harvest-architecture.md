# Harvest Architecture: The Integration of Scavenged Tech

## 1. Overview
This document defines the architectural strategy for integrating key components harvested from the `memodb-io` repository ecosystem (`nano-manus`, `drive-flow`, `prompt-string`, `memobase`). The goal is to enhance Khala's capabilities while maintaining its core stack: **SurrealDB**, **Agno**, and **Gemini**.

## 2. Component Integration Map

| Source Repo | Harvested Feature | Khala Target Component | Implementation Strategy |
| :--- | :--- | :--- | :--- |
| `nano-manus` | `Planner` Loop & `parse_step` | `KhalaPlanner` (New) | Replace logic in `PlanningService` with an Agno-compatible agent loop. |
| `drive-flow` | `EventEngine` & `EventGroup` | `CognitiveCycleEngine` | Implement a DAG-based reasoning engine for internal agent thought processes, persisted via SurrealDB. |
| `prompt-string` | `PromptString` Object | `khala.domain.prompt.utils` | Replace raw f-strings in `PromptOptimizationService` and `GeminiClient` with object-oriented prompts. |
| `memobase` | `Blob` & `Entry` abstractions | `KhalaClient` (SDK) | Create a user-facing Python SDK (`khala-py`) that mirrors `memobase`'s clean API but talks to Khala's REST/Surreal endpoints. |

## 3. Detailed Architecture

### 3.1. The New Planner (`KhalaPlanner`)
*Ref: `nano-manus/src/nano_manus/planner/planner.py`*

Instead of a single-shot Gemini call (current `PlanningService`), we implement an iterative "Plan -> Execute -> Verify" loop.

*   **State Persistence:** The `ExecutionPlan` and `PlanStep` entities (already in `planning_service.py`) will be enhanced.
*   **Logic:**
    1.  **Decompose:** Use `nano-manus` style `parse_step` regex/logic (adapted for Gemini) to break goals into steps.
    2.  **Dispatch:** Each step is dispatched to a specific "Worker". In Khala, a "Worker" is an **Agno Tool** or a **Sub-Agent**.
    3.  **Loop:** The `Planner` runs a `while` loop, checking step completion and refining the plan dynamically (Strategy 52 + Refinement Loops).

### 3.2. Cognitive Cycle Engine (Event-Driven Reasoning)
*Ref: `drive-flow/drive_flow/core.py`*

We will adapt `drive-flow` to create a **Cognitive Cycle** for agents. This is *not* a distributed job queue (we have `JobProcessor` for that), but a **micro-orchestrator** for a single agent's thought process.

*   **Concept:** An agent's "Thought" is a flow of Events: `Perceive` -> `Retrieve` -> `Reason` -> `Act`.
*   **Implementation:**
    *   `CognitiveEvent`: Base class for events (replacing `drive-flow.BaseEvent`).
    *   `CognitiveEngine`: Manages the flow.
    *   **SurrealDB Integration:** The "Broker" in `drive-flow` will be `SurrealDBEventBroker`. It pushes major state changes to the `audit_log` or `agent_trace` table, allowing "Time Travel" debugging (Strategy 76).

### 3.3. Prompt Engineering 2.0
*Ref: `prompt-string`*

We will adopt the `PromptString` pattern to make prompts composable and type-safe.

*   **Structure:**
    ```python
    from khala.domain.prompt.utils import PromptString, System, User

    # Composable prompts
    base_context = System("You are Khala.")
    task_prompt = User("Analyze this memory.")
    full_prompt = base_context + task_prompt
    ```
*   **Benefit:** Allows easier injection of `Memory` context into prompts without messy string concatenation errors.

### 3.4. Khala Client SDK
*Ref: `memobase/memobase-client`*

We will create a structured SDK for external python apps to use Khala.

*   **Location:** `khala/interface/sdk/` (New module).
*   **Design:**
    *   `KhalaClient`: Main entry point.
    *   `Blob`: Handling images/files (for Gemini Multimodal).
    *   `MemoryEntry`: Client-side representation of a Memory.
    *   **Transport:** Uses `httpx` to talk to Khala's FastAPI endpoints (defined in `khala/interface/rest`).

## 4. SurrealDB Native Integration Specifics

*   **Events:** `drive-flow` events will optionally be marked as `persistent`. If `persistent=True`, they are written to a SurrealDB table `event_stream`.
*   **Planner State:** The `Planner` object itself is stateless between ticks, but it rehydrates its state from `plan_execution` table in SurrealDB.
*   **Locking:** Uses `SurrealDBLock` (once fixed) for distributed coordination if multiple planners run.

## 5. TDD Strategy

All new components will be built test-first:
1.  `test_prompt_string.py` -> Implement `PromptString`.
2.  `test_cognitive_engine.py` -> Implement `CognitiveEngine`.
3.  `test_khala_planner.py` -> Implement `KhalaPlanner`.
