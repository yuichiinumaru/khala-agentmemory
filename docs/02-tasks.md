# 02-TASKS.md: The Execution Queue

**Status**: ACTIVE
**Phase**: 3.2 (Surgical Intervention) -> 4.0 (Cognitive Evolution)

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

## 🧠 PHASE 4: COGNITIVE EVOLUTION (Titans/MIRAS)

### 1. The Surprise Metric
- [ ] **Schema: Add Surprise Fields**
    -   **File**: `khala/domain/memory/entities.py`
    -   **Action**: Add `surprise_score` (float), `surprise_momentum` (float), `last_surprise_update` (datetime).
    -   **DB**: Update `schema.py` to define defaults.

- [ ] **Logic: Implement Surprise Calculation**
    -   **File**: `khala/application/services/surprise_service.py`
    -   **Action**: Implement `calculate_surprise(content, history)` using Embedding Distance + LLM Perplexity (simulated via logprobs if available or heuristic).

- [ ] **Pipeline: Integrate Surprise into Ingestion**
    -   **File**: `khala/application/services/memory_lifecycle.py`
    -   **Action**: In `ingest_memory`, calculate surprise. If > Threshold, force `LONG_TERM` promotion immediately.

### 2. Retention Gates & Momentum
- [ ] **Schema: Add Retention Fields**
    -   **File**: `khala/domain/memory/entities.py`
    -   **Action**: Add `retention_weight` (float, default 1.0).

- [ ] **Logic: Implement Retention Decay**
    -   **File**: `khala/domain/memory/services/decay_service.py`
    -   **Action**: Implement formula $w_{t+1} = \lambda w_t + \alpha f(surprise)$.
    -   **Job**: Update `JobProcessor` to run retention updates.

- [ ] **Logic: Implement Context Momentum**
    -   **File**: `khala/application/services/memory_lifecycle.py`
    -   **Action**: When a high-surprise event occurs, fetch neighbors (±N) and boost their `retention_weight` (Momentum).

### 3. Deep Memory (Derivation)
- [ ] **Schema: Derivation Edges**
    -   **File**: `khala/infrastructure/surrealdb/schema.py`
    -   **Action**: Define `derives_into` edge type for `Raw -> Episode -> Pattern`.

- [ ] **Logic: Deep Consolidation**
    -   **File**: `khala/domain/memory/services/consolidation_service.py`
    -   **Action**: Instead of merging, create a new "Parent" memory and link via `derives_into`.

### 4. Benchmarking
- [ ] **Test: Long Context Recall**
    -   **File**: `tests/stress/test_long_context.py`
    -   **Action**: Create a "Needle in a Haystack" test using 10k mock memories in SurrealDB and verifying `get_context` retrieval accuracy.

---

## 🗑️ BACKLOG (Future)

- [ ] Implement Module 15 (Version Control).
- [ ] Refactor `SpatialMemoryService`.
