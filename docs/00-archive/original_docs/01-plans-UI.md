# Plan: Khala Console (Supernova Transformation)

**Status**: ACTIVE
**Parent**: `docs/khala-integration-report.md`
**Target**: `khala-console` (v1.0)

---

## 1. The Mission
Transform the experimental `supernova-dashboard` into **Khala Console**, a mission-critical observability platform for AI Agents.
**Core Philosophy**: "If you can't see the thought, you can't trust the agent."

## 2. Architecture & Constraints

### 2.1. The "Surreal-Bridge" Hybrid Pattern
*   **READS**: Direct WebSocket to SurrealDB (`live select`).
    *   *Why*: Latency. We need 60fps updates for the graph physics.
    *   *Constraint*: Read-Only access tokens for the frontend.
*   **WRITES**: REST API to Khala Backend (`FastAPI`).
    *   *Why*: Integrity. All state changes must pass through Domain Services (`MemoryLifecycleService`).
    *   *Constraint*: No direct `INSERT/UPDATE` from the UI.

### 2.2. The Tech Stack
*   **Frontend**: React 19, Vite, TailwindCSS (Zinc/Purple theme).
*   **Visualization**:
    *   **2D (Tactical)**: `sigma.js` + `graphology` (Existing, optimize for 10k nodes).
    *   **3D (Strategic)**: `react-force-graph-3d` (New, for "Galaxy View").
*   **State Management**: `zustand` (Lightweight) + `tanstack-query` (API caching).
*   **Testing**: `vitest` + `react-testing-library`. **Strict TDD**.

---

## 3. Implementation Phases

### Phase 1: Foundation (The Skeleton)
*Goal: Establish the data pipeline and basic visualization.*
1.  **Rename & Clean**: Rename repo/folder to `khala-console`. Remove unused legacy code.
2.  **Surreal Connection**: Implement the WebSocket provider (`useSurreal`).
3.  **Live Graph**: Connect `GraphCanvas` to the `memory` table via `LIVE SELECT`.
4.  **Agent HUD**: Build the `AgentStatusWidget` fetching from `jobs`.

### Phase 2: Observability (The Eyes)
*Goal: Visualize the invisible metrics.*
1.  **Metric Pipelines**: Implement `EntropyService` APIs in backend.
2.  **Visualizers**: Create `EntropyGauge`, `VectorHeatmap`, and `MemoryInspector`.
3.  **Time Travel**: Implement the `TimelineScrubber` and state reconstruction logic.

### Phase 3: Interaction & Security (The Hands & Shield)
*Goal: Control and Protect.*
1.  **GhostEI Viz**: Implement the Security Layer visualization (Injection alerts).
2.  **The Oracle**: Connect `GraphOracle` chat to the Analyst Agent.
3.  **Dream Mode**: Implement the idle-state physics simulation.

---

## 4. Risks & Mitigations

| Risk | Mitigation |
| :--- | :--- |
| **Performance** | Use WebWorkers for graph physics. Implement "Super-Node" clustering for L1 zoom. |
| **Security** | Sanitize all HTML in `MemoryInspector`. Sandbox the Oracle. |
| **Drift** | Strict TDD. Frontend tests must mock the SurrealDB socket. |

---

## 5. Definition of Done (DoD)
1.  **Verified**: All 3 Critical User Stories (Hallucination Hunt, Optimization, Security) are performant.
2.  **Tested**: Unit test coverage > 80%.
3.  **Documented**: Updated `README.md` with setup instructions.
