# Task List: Khala Console Implementation

**Status**: PENDING
**Plan**: `docs/01-plans-UI.md`
**Context**: `khala-console` (formerly `supernova-dashboard`)

---

## 🟢 Phase 1: Foundation (The Skeleton)

### **TASK-UI-01: Project Rename & Cleanup**
*   **Description**: Official rename and cleanup of the submodule.
*   **Subtasks**:
    *   [ ] Rename `external/supernova-dashboard` to `external/khala-console`.
    *   [ ] Update `package.json` name to `@khala/console`.
    *   [ ] Remove `TASKS.md` and `Execution_Report.md` (legacy).
    *   [ ] Verify `npm install` and `npm run dev` still work.

### **TASK-UI-02: SurrealDB Connection Hook (TDD)**
*   **Description**: Implement a robust WebSocket hook for SurrealDB.
*   **Subtasks**:
    *   [ ] **Test**: Create `src/hooks/__tests__/useSurreal.test.tsx`.
        *   Test connection success case.
        *   Test authentication failure case.
        *   Test auto-reconnect logic.
    *   [ ] **Impl**: Install `surrealdb.js`.
    *   [ ] **Impl**: Create `SurrealProvider` context and `useSurreal` hook.
    *   [ ] **Verify**: All tests pass.

### **TASK-UI-03: Live Graph Data Pipeline (TDD)**
*   **Description**: Fetch nodes/edges from `memory` table using Live Queries.
*   **Subtasks**:
    *   [ ] **Test**: Create `src/services/__tests__/graphService.test.ts`.
        *   Mock SurrealDB client.
        *   Test `subscribeToGraph` transforms `memory` records into `graphology` graph object.
        *   Test handling of `CREATE`, `UPDATE`, `DELETE` events.
    *   [ ] **Impl**: Implement `GraphService.ts`.
    *   [ ] **Impl**: Update `useGraphApplication.ts` to use `GraphService`.
    *   [ ] **Verify**: Tests pass.

### **TASK-UI-04: Agent Status Widget (TDD)**
*   **Description**: The "Heartbeat" widget in the HUD.
*   **Subtasks**:
    *   [ ] **Test**: Create `src/components/__tests__/AgentStatusWidget.test.tsx`.
        *   Render with `status="thinking"`. Verify green indicator.
        *   Render with `status="error"`. Verify red border.
        *   Update props -> verify text change.
    *   [ ] **Impl**: Create `AgentStatusWidget.tsx` (Use `lucide-react` icons).
    *   [ ] **Verify**: Tests pass.

---

## 🟡 Phase 2: Observability (The Eyes)

### **TASK-UI-05: Memory Inspector Component (TDD)**
*   **Description**: The details panel when a node is clicked.
*   **Subtasks**:
    *   [ ] **Test**: Create `src/components/__tests__/MemoryInspector.test.tsx`.
        *   Test rendering of `MemoryNode` props (content, tier, importance).
        *   Test `HTML` sanitization (inject `<script>alert(1)</script>` and ensure it is stripped).
        *   Test "Vector Tab" is hidden if no embedding.
    *   [ ] **Impl**: Create `MemoryInspector.tsx` using `react-markdown` and `dompurify`.
    *   [ ] **Verify**: Tests pass.

### **TASK-UI-06: Timeline Scrubber (TDD)**
*   **Description**: Time-travel control.
*   **Subtasks**:
    *   [ ] **Test**: Create `src/components/__tests__/TimelineScrubber.test.tsx`.
        *   Test slider change fires `onChange`.
        *   Test rendering of event markers (correct % position).
    *   [ ] **Impl**: Create `TimelineScrubber.tsx`.
    *   [ ] **Verify**: Tests pass.

### **TASK-UI-07: Entropy Gauge (TDD)**
*   **Description**: Visualizing System Health.
*   **Subtasks**:
    *   [ ] **Test**: Create `src/components/__tests__/EntropyGauge.test.tsx`.
        *   Test color interpolation (Green -> Yellow -> Red) based on value.
    *   [ ] **Impl**: Create `EntropyGauge.tsx` (SVG based or chart lib).
    *   [ ] **Verify**: Tests pass.

---

## 🔴 Phase 3: Interaction (The Hands)

### **TASK-UI-08: Analyst Agent API Client (TDD)**
*   **Description**: Connect to the backend Analyst Service.
*   **Subtasks**:
    *   [ ] **Test**: Create `src/services/__tests__/analystService.test.ts`.
        *   Mock `fetch`.
        *   Test `getTrace(jobId)` parsing.
        *   Test `getMetrics()` error handling.
    *   [ ] **Impl**: Create `AnalystService.ts`.
    *   [ ] **Verify**: Tests pass.

### **TASK-UI-09: Graph Oracle Integration (TDD)**
*   **Description**: Update the Chat Window to use the Analyst API.
*   **Subtasks**:
    *   [ ] **Test**: Create `src/components/__tests__/GraphOracle.test.tsx`.
        *   Test sending message calls API.
        *   Test receiving JSON action (`FOCUS_NODE`) triggers callback.
    *   [ ] **Impl**: Refactor `GraphOracle.tsx`.
    *   [ ] **Verify**: Tests pass.

### **TASK-UI-10: Dream Mode Physics (Visual)**
*   **Description**: Idle state simulation.
*   **Subtasks**:
    *   [ ] **Impl**: Create `DreamModeController.ts`.
    *   [ ] **Impl**: Add logic to `App.tsx` to detect 5m idle -> toggle Dream Mode.
    *   [ ] **Verify**: Manual verification (hard to TDD physics viz).

---

## 🛠️ Infrastructure & cleanup

### **TASK-UI-11: E2E Verification**
*   **Description**: Playwright test for critical flows.
*   **Subtasks**:
    *   [ ] Create `tests/e2e/login.spec.ts`.
    *   [ ] Create `tests/e2e/graph_navigation.spec.ts`.
