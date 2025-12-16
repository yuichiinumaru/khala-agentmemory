# 19-SURREALIST-ANALYSIS.md: UI & WASM Plugins

**Source**: Official Documentation (Dec 2025)
**Scope**: Surrealist UI for Administration and Surrealism (WASM) for Logic Offloading.
**Status**: Analysis & Integration Plan

---

## 1. Surrealist UI (Admin & Monitoring)

Surrealist is the official GUI for SurrealDB. It offers Query, Explorer, Designer, and Authentication views.

### Relevance to Khala
Khala currently lacks a dedicated Admin Dashboard. Building one in React/FastAPI is expensive. Surrealist can serve as the **Zero-Code Admin Panel**.

### Key Features for Khala
1.  **Graph Visualization**: The *Explorer View* allows traversing record links. We can visualize the `memory` -> `links` -> `memory` graph without writing code.
2.  **Schema Designer**: The *Designer View* helps visualize the schema dependencies (e.g., `Memory` vs `AgentProfile`).
3.  **Saved Queries**: We can distribute a `khala_admin.surql` file containing "Saved Queries" for common tasks:
    *   `Maintenance: Prune Decayed Memories`
    *   `Stats: Memory Count by Agent`
    *   `Debug: Find Orphaned Nodes`

### Implementation Plan
-   **Artifact**: Create `docs/sops/sop-04-surrealist-setup.md`.
-   **Configuration**: Create `scripts/surrealist_queries.json` (or SQL export) to import into Surrealist.

---

## 2. Surrealism (WASM Plugins)

Surrealism allows executing compiled Rust/WASM code *inside* the database. This is a game-changer for performance and consistency.

### Relevance to Khala
Khala currently performs logic in Python (Application Layer). Moving "Pure Domain Logic" to WASM (Infrastructure/Data Layer) reduces network roundtrips and serialization overhead.

### High-Value Use Cases
1.  **Entropy Calculation (Consolidation)**:
    *   *Current*: Python fetches memories -> Calculates Entropy -> Updates DB.
    *   *Surrealism*: Python calls `UPDATE memory SET entropy = fn::calculate_entropy(content)`.
    *   *Benefit*: O(1) network call instead of O(N) fetch.
2.  **Sanitization (Security)**:
    *   *Current*: Python regex/logic.
    *   *Surrealism*: `fn::sanitize_input(content)` runs closer to storage.
3.  **Vector Operations**:
    *   If SurrealDB's native vector ops are limited, we can implement custom distance metrics in Rust/WASM.

### Challenges
-   **Complexity**: Requires Rust toolchain and compilation steps (`surrealism build`).
-   **Deployment**: Must mount `.surli` files to the DB container.
-   **Experimental Flag**: Requires `SURREAL_CAPS_ALLOW_EXPERIMENTAL`.

### Strategy
We will adopt a **"WASM-Lite"** strategy. We will not rewrite the core application, but we will offload *compute-heavy, data-local* functions to WASM where Python is a bottleneck.

---

## 3. Integration Tasks

### Phase 1: Surrealist Adoption (Immediate)
-   [ ] Document connection settings for local/docker SurrealDB.
-   [ ] Create a library of "Standard Operating Queries" (SOQ) for admins.

### Phase 2: Surrealism Prototype (Experimental)
-   [ ] Set up a Rust/WASM build pipeline in `khala/infrastructure/surrealism/`.
-   [ ] Implement `fn::calculate_entropy(text)` as a POC.
-   [ ] Benchmark Python vs WASM implementation.
