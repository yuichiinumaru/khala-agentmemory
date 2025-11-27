# Grand Unified Audit: Master Fix Queue

This document outlines the prioritized tasks for the Execution Cycle (Phase 5), based on the findings from the Integrity Scan, Technical Deep Scan, and Stress Test.

## Priority 1: Tech Debt & Testing Foundation

*   **Rationale:** The codebase is secure but architecturally unsound and lacks any tests. Addressing the technical debt and establishing a testing foundation is the highest priority to ensure future stability and maintainability.

---

### **TASK-01: Establish Testing Infrastructure**
*   **Status:** PENDING
*   **Description:** Install and configure a modern testing framework to enable unit and component testing.
*   **Acceptance Criteria:**
    *   `vitest` and `@testing-library/react` are added as dev dependencies.
    *   `vite.config.ts` is configured for `vitest`.
    *   A basic test command can be run successfully.

---

### **TASK-02: Write Unit Tests for Core Logic (TDD)**
*   **Status:** PENDING
*   **Description:** Write unit tests for the pure functions in `core/algorithms.ts`. This ensures the business logic is correct before refactoring the application structure.
*   **Acceptance Criteria:**
    *   `core/algorithms.test.ts` is created.
    *   Tests for `getGraphStats`, `summarizeGraphContext`, and `summarizeViewport` are implemented.
    *   All tests pass with 100% coverage for the file.

---

### **TASK-03: Refactor File Structure**
*   **Status:** PENDING
*   **Description:** Reorganize the codebase to match the documented "Modolith" architecture.
*   **Acceptance Criteria:**
    *   A `src/` directory is created.
    *   All source files (`App.tsx`, `components/`, `core/`, `hooks/`, `services/`, `types.ts`, `index.tsx`) are moved into `src/`.
    *   `index.html`, `vite.config.ts`, and `tsconfig.json` are updated to reflect the new paths.
    *   The application runs correctly after the file structure change.

---

### **TASK-04: Deconstruct `App.tsx` Monolith**
*   **Status:** PENDING
*   **Description:** Refactor the "god component" `App.tsx` into smaller, single-responsibility components and move state management into the appropriate hooks.
*   **Acceptance Criteria:**
    *   New components are created for distinct UI sections (e.g., `Header.tsx`, `HudControls.tsx`, `NodeInspector.tsx`).
    *   State and logic related to graph visualization are moved from `App.tsx` into `hooks/useGraphViz.ts`.
    *   `App.tsx` is simplified to primarily a layout and composition root.

---

## Priority 2: Documentation

*   **Rationale:** Once the codebase is refactored, the documentation must be updated to reflect the new reality.

---

### **TASK-05: Update Architecture Documentation**
*   **Status:** PENDING
*   **Description:** Synchronize `docs/03-architecture.md` with the refactored codebase.
*   **Acceptance Criteria:**
    *   The directory structure diagram in the document is updated.
    *   The Mermaid graph accurately reflects the new component hierarchy and data flow.
    *   The description of the data flow is updated to mention the new components.
