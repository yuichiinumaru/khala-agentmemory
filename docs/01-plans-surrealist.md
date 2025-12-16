# Plan: Surreal Ecosystem Integration

**Status**: Draft
**Phase**: 5 (Infrastructure & Optimization)
**Owner**: Jules

## 1. Executive Summary
Integrate Surrealist as the primary Admin UI and explore Surrealism (WASM) for high-performance logic offloading. This aligns with Khala's philosophy of leveraging the underlying engine capabilities to the fullest.

## 2. Core Objectives
1.  **Admin UI**: Zero-code dashboard for memory inspection and graph traversal.
2.  **Performance**: Offload O(N) scoring/entropy logic to O(1) DB-local WASM functions.

## 3. Implementation Plan

### 3.1. Surrealist Setup (Low Effort)
*Goal:* Enable developers to debug graph states visually.
*   **Actions:**
    *   Update `README.md` with "Recommended Tool: Surrealist".
    *   Create `docs/sops/sop-04-surrealist-setup.md`.
    *   Commit `scripts/surrealist_queries.surql` with common debug queries.

### 3.2. Surrealism WASM Pipeline (High Effort)
*Goal:* Establish a build chain for Database Functions.
*   **Actions:**
    *   Create `khala/infrastructure/surrealism/Cargo.toml`.
    *   Implement `entropy.rs` (Shannon entropy calculation).
    *   Create `scripts/build_wasm.sh`.
    *   Update `docker-compose.yml` to mount `.surli` files and enable experimental flags.

## 4. Risks & Mitigations
*   **Risk**: WASM debugging is difficult.
    *   *Mitigation*: Unit test Rust code heavily before compilation.
*   **Risk**: "Experimental" flag stability.
    *   *Mitigation*: Keep WASM logic non-critical (optimization only) until stable.
