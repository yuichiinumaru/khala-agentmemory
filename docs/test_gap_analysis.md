# Test Gap Analysis Report

**Date:** 2025-12-04
**Scope:** 170 Strategies vs `khala/tests/`

## 1. Overview
The current test suite consists of ~8 files located in `khala/tests/unit/`. It primarily covers recent additions (Module 11, 12, 13, 14, 15, 16). Coverage for core strategies (Modules 1-10) is sparse or implicitly covered only via integration in higher-level services.

## 2. Coverage Analysis by Module

### Module 1: Core Strategies (1-22)
*   **Status:** **CRITICAL GAP**
*   **Missing Tests:**
    *   Basic CRUD for Vector/Graph/Document (Strats 1-3).
    *   RBAC (Strat 4) - Feature disabled, but tests missing regardless.
    *   LIVE Subscriptions (Strat 5).
    *   Context Assembly (Strat 8).
    *   Background Jobs (Strat 13) - `scheduler.py` has no specific tests.
*   **Existing:** `test_memory_lifecycle.py` covers some promotion/decay logic (Strats 10, 21), but purely at service level.

### Module 2: Advanced Intelligence (23-57)
*   **Status:** **PARTIAL**
*   **Missing Tests:**
    *   LLM Cascading (Strat 23) - `GeminiClient` has no direct unit tests, only mocked usage in other services.
    *   Multi-Agent Debate (Strat 27) - Referenced in mocks but no dedicated test file.
    *   Multimodal (Strats 49-50) - No tests found.
    *   Planning/Hypothesis (Strats 52-54) - No tests found.
*   **Existing:** `test_module_13.py` covers PromptWizard/ARM (Strats 160, 161). `test_privacy_safety.py` covers some safety aspects.

### Module 3: SurrealDB Optimization (58-115)
*   **Status:** **GOOD (Recent)**
*   **Existing:**
    *   `test_modules_11_12.py` covers:
        *   Strat 67 (Bi-temporal Graph).
        *   Strat 71 (Recursive Graph).
        *   Strat 121 (Graph Reranking).
    *   `test_vector_ops.py` covers Strats 79-84 (Quantization, Drift, Clustering).
*   **Gaps:**
    *   Geospatial (111-115) - `SpatialMemoryService` is broken (syntax error) and HAS NO TESTS.
    *   Consensus Graph (73) - Missing.

### Module 4: Novel & Experimental (116-159)
*   **Status:** **PARTIAL**
*   **Existing:**
    *   `test_memory_lifecycle.py` covers Strat 152 (Bias Detection via PrivacyService integration) and Strat 129 (Dream - implicit).
    *   `test_dr_mamr.py` covers Strat 168 (Meta-Reasoning).
*   **Gaps:**
    *   Strat 116 (Flows/Crews) - Feature missing.
    *   Strat 126 (Semaphore) - Feature missing.
    *   Strat 158 (Merge Conflict) - Service exists but no specific tests in `test_modules_11_12.py`.

### Module 5: Research Integration (160-170)
*   **Status:** **VERY GOOD**
*   **Existing:**
    *   `test_module_13.py` & `test_module_13_advanced.py` cover Strats 160-165 extensively.
    *   `test_dr_mamr.py` covers Strat 168.
*   **Gaps:**
    *   MarsRL (166) - `mars_rl_service.py` exists but has no corresponding test file.

## 3. Critical Strategy Gaps (Priority Fixes)

1.  **Spatial Memory (111-115):** Code is broken, 0 tests.
2.  **Multimodal (49, 50, 78):** Code exists, 0 tests.
3.  **Merge/Branch (156-158):** Critical data integrity features, 0 tests.
4.  **Gemini Client (23, 126):** Core infrastructure, 0 direct tests (only mocks).
5.  **Graph Analysis (143-146):** Centrality/Isomorphism implemented but not tested.

## 4. Recommendations for Unified Test Suite

*   **Structure:** Create `khala/tests/integration/` for end-to-end flows.
*   **Runner:** Use `pytest` with custom markers (`@pytest.mark.strategy("123")`) to allow executing tests by Strategy ID.
*   **Reporting:** Integrate `pytest-html` or `pytest-json-report` to map pass/fail status back to the Strategy List.
