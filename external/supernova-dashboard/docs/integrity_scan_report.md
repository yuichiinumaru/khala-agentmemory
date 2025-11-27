# Integrity Scan Report (Phase 1)

## Summary
The Integrity Scan reveals a significant drift between the documented architecture and the implemented codebase. The project is functional, but the code structure does not follow the "Modolith" design outlined in `docs/03-architecture.md`.

## Key Discrepancies (δ Score: High)

1.  **Missing `src` Directory:** The codebase is in the root directory, not within a dedicated `src` folder as documented.
2.  **Incorrect Directory Structure:**
    *   **Expected:** `core/`, `rendering/`, `hooks/`, `components/`, `services/`, `styles/`
    *   **Actual:** `core/`, `hooks/`, `components/`, `services/` (Missing `rendering` and `styles`).
3.  **Architectural Mismatch:**
    *   The application's state and UI logic are almost entirely centralized in `App.tsx`.
    *   This contradicts the layered architecture, which intended to separate concerns into different modules (e.g., `useGraphViz.ts` as a controller, `components/` for UI).
4.  **Incomplete Tasks:**
    *   The "Code Organization" task in `docs/02-tasklist.md` is marked as incomplete, which is the root cause of the structural issues.
5.  **Undocumented Complexity:**
    *   `App.tsx` has grown into a large, complex component that manages state, UI, and interactions, making it difficult to maintain and understand. This complexity is not documented.

## Conclusion
The high documentation drift score (δ) indicates that the immediate priority should be a technical debt cleanup. The codebase needs to be refactored to align with the intended architecture *before* adding new features. This will improve maintainability and scalability.