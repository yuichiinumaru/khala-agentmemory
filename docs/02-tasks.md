# 02-TASKS.md: The Execution Queue

**Status**: ACTIVE
**Phase**: 3.2 - Surgical Intervention (Resurrection)

---

## 🚨 CRITICAL (Must Fix Immediately)

- [x] **Security: Fix CLI Executor RCE**
    -   **File**: `khala/infrastructure/executors/cli_executor.py`
    -   **Action**: Used `shutil.which` and absolute path.

- [x] **Security: Fix CLI Executor DoS**
    -   **File**: `khala/infrastructure/executors/cli_executor.py`
    -   **Action**: Implemented `_read_stream_safe` with 10MB limit.

- [x] **Data Integrity: Fix Timestamp Corruption**
    -   **File**: `khala/infrastructure/surrealdb/client.py`
    -   **Action**: `parse_dt` raises `ValueError` on None/Invalid.

- [x] **Concurrency: Fix Duplicate Race Condition**
    -   **File**: `khala/infrastructure/surrealdb/client.py`
    -   **Action**: Improved error handling to catch DB unique constraint violations.

- [x] **Dependency: Fix setup.py**
    -   **File**: `setup.py`
    -   **Action**: Confirmed `surrealdb>=2.0.4` is pinned.

## 🟠 HIGH (Stability & Correctness)

- [x] **Infrastructure: Add Cloud SurrealDB Support**
    -   **File**: `khala/infrastructure/surrealdb/client.py`
    -   **Action**: Add token-based authentication support to `SurrealConfig` and `SurrealDBClient`.

- [x] **Performance: Fix API Auth Bottleneck**
    -   **File**: `khala/interface/rest/main.py`
    -   **Action**: Config loaded once in `lifespan` into `state.api_key`.

- [x] **Reliability: Fix Gemini Batch Errors**
    -   **File**: `khala/infrastructure/gemini/client.py`
    -   **Action**: `generate_embeddings` fails loudly on batch error to preserve alignment.

- [ ] **Performance: Fix Lifecycle LLM Loop**
    -   **File**: `khala/application/services/memory_lifecycle.py`
    -   **Issue**: Sequential LLM calls in `consolidate_memories`.
    -   **Action**: Refactor to use `asyncio.gather` with semaphore throttling.

- [ ] **Persistence: Fix SOP Registry**
    -   **File**: `khala/domain/sop/services.py`
    -   **Issue**: In-memory storage (`self._sops`).
    -   **Action**: Inject `SOPRepository` and implement persistence.

- [x] **Type Safety: Fix Model Metrics**
    -   **File**: `khala/infrastructure/gemini/models.py`
    -   **Action**: Used `UsageStats` dataclass with integers.

## 🟡 MEDIUM (Refactoring)

- [x] **Hygiene: Deduplicate JSON Parsing**
    -   **File**: `khala/infrastructure/gemini/client.py`
    -   **Action**: Imported `parse_json_safely` from `khala.application.utils`.

- [x] **Architecture: Fix Local Imports**
    -   **File**: `khala/infrastructure/surrealdb/client.py`
    -   **Action**: Moved imports to top level.

- [x] **Stability: Fix API Startup**
    -   **File**: `khala/interface/rest/main.py`
    -   **Action**: `lifespan` raises `RuntimeError` on startup failure.

---

## 🗑️ BACKLOG (Future)

- [ ] Implement Module 15 (Version Control).
- [ ] Refactor `SpatialMemoryService`.
