# 01-PLAN.md: KHALA v2.1 Project Plan

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)
**Version**: 2.1 (Resurrection)
**Framework**: Agno + SurrealDB
**Date**: December 2025
**Status**: STRUCTURAL RESURRECTION

---

## 1. Executive Summary

### Project Vision
Resurrect and harden the KHALA memory system into a production-grade, secure, and reliable foundation. The Autopsy (Dec 2025) revealed critical structural and security failures. We are now in the "Resurrection Era".

### Core Objective
Systematic elimination of fragility. Fix critical security holes, data corruption bugs, and architectural deviations.

### Key Deliverables
1.  **Governance Enforcement**: `AGENTS.md` is the law. `docs/` is the truth.
2.  **Security Hardening**: Eliminate RCE and DoS vectors.
3.  **Data Integrity**: Ensure timestamps and versions are immutable and correct.
4.  **Performance Optimization**: Remove O(N) loops and blocking I/O.

---

## 2. Project Scope

### Phase 3.1: Structural Resurrection (Current)
-   [x] Governance Audit & File Cleanup.
-   [x] Documentation Alignment (`01`, `02`, `03`).
-   [x] Task Purification.

### Phase 3.2: Surgical Intervention (Next)
-   [ ] **Critical Security Fixes**: CLI Executor, API Auth.
-   [ ] **Data Integrity Fixes**: SurrealDB Client.
-   [ ] **Reliability Fixes**: Gemini Client, Lifecycle Service.

### Phase 3.3: Wisdom Ingestion (The Harvest)
-   [ ] **Security Hardening**: Implement "Attention-based" defenses against injection (GhostEI).
-   [ ] **Memory Architecture**: Adopt "Entropy-Based" consolidation (O-Mem).
-   [ ] **Agent Evolution**: Enable "Self-Correction" loops (ReflexGrad).
-   See `docs/18-wisdom-ingestion.md` for details.

### Phase 3.4: Advanced Features (Deferred)
-   Module 15 (Version Control).
-   Optimization Strategies.

---

## 3. Implementation Strategy

1.  **Stop the Bleeding**: No new features until Critical tasks in `02-tasks.md` are closed.
2.  **Verify Every Stitch**: Use TDD where possible. Verify fixes with `read_file` or reproduction scripts.
3.  **Fail Fast**: Crash on error. Do not swallow exceptions.
4.  **Zero Trust**: Trust no input, trust no path.

---

## 4. Progress Tracking
See `docs/02-tasks.md` for the active execution queue.
