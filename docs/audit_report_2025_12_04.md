# Codebase Audit Report - 2025-12-04

## Overview
This report documents a rigorous audit of the `khala` codebase against the project documentation and the 170 strategies listed in `README.md`.

**Audit Date:** 2025-12-04
**Auditor:** Jules (AI Agent)
**Scope:** Entire `khala/` directory and `docs/`.

## Critical Issues & Blockers

### 1. Spatial Memory Service Syntax Error
*   **File:** `khala/application/services/spatial_memory_service.py`
*   **Issue:** Critical syntax error in `find_within_region` method. Triple quotes for the SQL query are not closed properly before Python code injection is attempted. The logic attempts to execute Python code (`coords_list = ...`) *inside* a SQL string definition, which is impossible.
*   **Impact:** The module is unparseable and unusable. Strategies 111-115 are effectively broken.

### 2. Missing "Flows vs Crews" Domain
*   **Strategy:** 116 (Flows vs Crews Pattern)
*   **Documentation Claim:** "Flows in `khala/domain/flow` and Crews in `khala/domain/crew`".
*   **Status:** **MISSING**. These directories do not exist.
*   **Impact:** Core architectural pattern is not implemented.

### 3. Semaphore Concurrency Limiting
*   **Strategy:** 126
*   **Documentation Claim:** `GeminiClient` uses `asyncio.Semaphore` (default 10).
*   **Status:** **MISSING**. `GeminiClient` implements retries and exponential backoff, but there is no `Semaphore` logic to limit concurrent requests.
*   **Impact:** Risk of rate limiting errors under high load.

## Implementation Gaps & Discrepancies

### 4. Hyperedge Implementation Mismatch
*   **Strategy:** 66 (Hyperedge Emulation)
*   **Documentation Claim:** "distinct Hyperedge entity (and hyperedge table)".
*   **Codebase Reality:** No `hyperedge` table in `schema.py`. `GraphService` emulates hyperedges by creating a "HyperNode" (Entity) and connecting participants via standard `Relationship` edges.
*   **Verdict:** Implementation exists (via emulation) but contradicts documentation about a specific table.

### 5. Consensus Graph Missing Fields
*   **Strategy:** 73 (Consensus Graph)
*   **Documentation Claim:** "distinguished by an `is_consensus` boolean field... in `Relationship` table".
*   **Codebase Reality:** `schema.py` defines `relationship` table but lacks `is_consensus` or `consensus_data` fields.
*   **Status:** **INCOMPLETE**.

### 6. RBAC Not Enabled
*   **Strategy:** 04 (RBAC Multi-Tenancy)
*   **Codebase Reality:** `rbac_permissions` is defined in `schema.py` but is commented out in the `creation_order` list.
*   **Status:** **DISABLED**.

### 7. Multimodal Retrieval Missing
*   **Strategy:** 50 (Cross-Modal Retrieval)
*   **Codebase Reality:** `MultimodalService.ingest_image` exists, but there is no logic for *retrieving* images based on text or vice-versa, nor a "Cross-Modal Retrieval" service. `TODO` comments found in grep.
*   **Status:** **INCOMPLETE**.

## Code Quality & Refactoring Opportunities

### 8. Python-in-SQL Logic
*   **File:** `khala/application/services/spatial_memory_service.py`
*   **Issue:** The code attempts to mix Python logic generation with string formatting in a way that suggests a misunderstanding of how the string will be evaluated (or it's just a copy-paste error).
*   **Recommendation:** Refactor to prepare data in Python first, then pass as parameters or valid JSON string to the query.

### 9. N+1 Query Risks
*   **File:** `GraphService.get_inherited_relationships`
*   **Issue:** Iterates through parents and runs a query for each parent.
*   **Recommendation:** Use a single query with `WHERE from_entity_id IN $parents`.

### 10. Hardcoded Models in Service
*   **File:** `MultimodalService.ingest_image`
*   **Issue:** Uses hardcoded `"models/multimodal-embedding-001"` and `"gemini-2.5-pro"` (in analysis fallback).
*   **Recommendation:** Use `ModelRegistry` for all model references.

## Strategy Verification Summary

| ID Range | Category | Status | Notes |
|----------|----------|--------|-------|
| 01-22 | Core | **Mostly Verified** | RBAC (04) disabled. |
| 23-57 | Advanced | **Mixed** | Multimodal (50) incomplete. |
| 58-115 | Optimization | **Mixed** | Spatial (111-115) broken syntax. Hyperedge (66) docs mismatch. Consensus (73) missing fields. |
| 116-159 | Novel | **Mixed** | Flows/Crews (116) missing. Semaphore (126) missing. Merge/Branch (156-158) Verified. |
| 160-170 | Research | **Verified** | MarsRL, Dr.MAMR, AgentsNet files exist and match schema. |
