# 02-TASKS.md: The Execution Queue

**Status**: ACTIVE
**Phase**: 3.2 - Surgical Intervention (Post-Autopsy)

---

## 🚨 CRITICAL (Must Fix Immediately)

- [ ] **Security: Purge `execution_evaluator.py`**
    -   **File**: `khala/application/services/execution_evaluator.py`
    -   **Action**: Delete the file. It contains unsafe `exec()` usage. Remove references in `khala/application/services/execution_service.py` (if exists) or other consumers.

- [ ] **Reliability: Fix Job Serialization**
    -   **File**: `khala/infrastructure/background/jobs/job_processor.py`
    -   **Action**: Replace `json.dumps(payload)` with a Pydantic-aware serializer to handle `datetime` objects.

- [ ] **Security: Secure CLI Defaults**
    -   **File**: `khala/interface/cli/main.py`
    -   **Action**: Remove default `root` password. Require `--password` arg or env var.

- [ ] **Logic: Relax Vector Validation**
    -   **File**: `khala/domain/memory/value_objects.py`
    -   **Action**: Update `EmbeddingVector` check to allow tolerance (e.g., `1.0001`) or remove strict `[-1, 1]` check for unnormalized models.

- [ ] **Dependency: Fix `setup.py`**
    -   **File**: `setup.py`
    -   **Action**: Pin `surrealdb>=2.0.4`. Fix `numpy` version to stable (e.g., `1.26.0`).

## 🟠 HIGH (Stability & Correctness)

- [ ] **Data Integrity: Fix Timestamp Parsing**
    -   **File**: `khala/infrastructure/surrealdb/client.py`
    -   **Action**: Fix `parse_dt` to raise errors on corruption instead of defaulting to `now()`.

- [ ] **Reliability: Fix Manual JSON Parsing**
    -   **File**: `khala/application/services/planning_service.py`
    -   **Action**: Replace manual regex JSON extraction with `khala.application.utils.parse_json_safely` (create utils if missing).

- [ ] **Performance: Configurable Search Weights**
    -   **File**: `khala/application/services/hybrid_search_service.py`
    -   **Action**: Move hardcoded boosting weights to `SurrealConfig` or a Strategy configuration.

## 🟡 MEDIUM (Refactoring)

- [ ] **Hygiene: Centralize PII Logic**
    -   **File**: `khala/application/services/privacy_safety_service.py`
    -   **Action**: Deduplicate JSON extraction logic.

---

## 🗑️ BACKLOG (Future)

- [ ] Implement Module 15 (Version Control) logic fully.
- [ ] Refactor `SpatialMemoryService` queries.
