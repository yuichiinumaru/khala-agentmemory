# 02-TASKS.md: The Execution Queue

**Status**: ACTIVE
**Phase**: 3.2 - Surgical Intervention (Resurrection)

---

## 🚨 CRITICAL (Must Fix Immediately)

- [ ] **Security: Fix CLI Executor RCE**
    -   **File**: `khala/infrastructure/executors/cli_executor.py`
    -   **Issue**: Implicit `npx` execution allows PATH hijacking.
    -   **Action**: Use absolute path for node binary, or validate `npx` path via `shutil.which`. Implement strict sandbox checks.

- [ ] **Security: Fix CLI Executor DoS**
    -   **File**: `khala/infrastructure/executors/cli_executor.py`
    -   **Issue**: `process.communicate()` reads unlimited output into memory.
    -   **Action**: Refactor to use `asyncio.StreamReader` and process output in chunks/limits.

- [ ] **Data Integrity: Fix Timestamp Corruption**
    -   **File**: `khala/infrastructure/surrealdb/client.py`
    -   **Issue**: `parse_dt` defaults to `now()` on missing input.
    -   **Action**: Raise `ValueError` if timestamp is missing. Do not falsify history.

- [ ] **Concurrency: Fix Duplicate Race Condition**
    -   **File**: `khala/infrastructure/surrealdb/client.py`
    -   **Issue**: Client-side hash check causes race conditions.
    -   **Action**: Implement DB-level UNIQUE constraint on `content_hash` and handle conflict via UPSERT/Merge.

## 🟠 HIGH (Stability & Correctness)

- [ ] **Performance: Fix API Auth Bottleneck**
    -   **File**: `khala/interface/rest/main.py`
    -   **Issue**: `os.getenv` called on every request.
    -   **Action**: Load config into `AppState` at startup.

- [ ] **Reliability: Fix Gemini Batch Errors**
    -   **File**: `khala/infrastructure/gemini/client.py`
    -   **Issue**: `generate_embeddings` swallows exceptions in loop.
    -   **Action**: Implement proper error aggregation and reporting.

- [ ] **Performance: Fix Lifecycle LLM Loop**
    -   **File**: `khala/application/services/memory_lifecycle.py`
    -   **Issue**: Sequential LLM calls in `consolidate_memories`.
    -   **Action**: Refactor to use `asyncio.gather` with semaphore throttling.

- [ ] **Persistence: Fix SOP Registry**
    -   **File**: `khala/domain/sop/services.py`
    -   **Issue**: In-memory storage (`self._sops`).
    -   **Action**: Inject `SOPRepository` and implement persistence.

- [ ] **Type Safety: Fix Model Metrics**
    -   **File**: `khala/infrastructure/gemini/models.py`
    -   **Issue**: Integers stored as strings.
    -   **Action**: Refactor `ModelMetrics` to use native `int`.

## 🟡 MEDIUM (Refactoring)

- [ ] **Hygiene: Deduplicate JSON Parsing**
    -   **File**: `khala/infrastructure/gemini/client.py`
    -   **Action**: Import `parse_json_safely` from `khala.application.utils`.

- [ ] **Architecture: Fix Local Imports**
    -   **File**: `khala/infrastructure/surrealdb/client.py`
    -   **Action**: Move `khala.domain.memory.entities` imports to top level. Use `TYPE_CHECKING` if needed.

- [ ] **Stability: Fix API Startup**
    -   **File**: `khala/interface/rest/main.py`
    -   **Action**: Remove `yield` on exception in `lifespan`. Fail fast.

---

## 🗑️ BACKLOG (Future)

- [ ] Implement Module 15 (Version Control).
- [ ] Refactor `SpatialMemoryService`.
