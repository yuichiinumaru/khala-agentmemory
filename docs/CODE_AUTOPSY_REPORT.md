# CODE AUTOPSY REPORT
**Pathologist:** Senior Engineer Forensic Pathologist
**Date:** 2025-05-27
**Subject:** KHALA Memory System
**Cause of Death:** Multiple Organ Failure (Logic, Security, Governance)

---

## Section 1: The File-by-File Breakdown (Deep Tissue Analysis)

**File:** `khala/domain/memory/entities.py`
**Shame Score:** 90
**Findings:**
* `[Line 126]` **(High)**: `should_promote_to_next_tier` checks `tier == SHORT_TERM` and promotes based on importance alone. This ignores age, potentially promoting brand new important memories instantly, violating the "long term" maturation concept.
* `[Line 141]` **(Good)**: `archive` method enforces business rules unless `force=True`.
* `[Line 223]` **(Nit)**: `Entity.confidence` validation logs a warning but clamps the value. This "Fail Open" behavior might mask upstream data corruption.

**File:** `khala/domain/memory/value_objects.py`
**Shame Score:** 85
**Findings:**
* `[Line 28]` **(Critical)**: `EmbeddingVector` validation `if not (-1 <= value <= 1)` is too strict for some unnormalized models. This will cause crashes in production if `1.0000001` floats appear.
* `[Line 125]` **(Med)**: `MemoryTier.ttl_hours` uses magic numbers (`15 * 24`). Define constant `SHORT_TERM_DAYS = 15`.

**File:** `khala/infrastructure/coordination/distributed_lock.py`
**Shame Score:** 95
**Findings:**
* `[Line 45]` **(Good)**: Uses `CREATE` for atomic exclusion.
* `[Line 38]` **(Good)**: Cleans up expired locks before acquisition to prevent deadlocks.
* `[Line 75]` **(Nit)**: `SurrealDBLock` takes `client` but has no type hint.

**File:** `khala/infrastructure/background/jobs/job_processor.py`
**Shame Score:** 80
**Findings:**
* `[Line 158]` **(Critical)**: `json.dumps(job.payload)` will crash if payload contains `datetime` objects, which is highly likely in a temporal system.
* `[Line 108]` **(High)**: `_process_job` calls `await asyncio.sleep(0.1)` in a tight loop. While responsive, it burns CPU if empty. Use `await self._memory_queue.get()` for blocking wait (event-driven).
* `[Line 330]` **(High)**: `_execute_decay_scoring` logic `response[0].get('result', response)` suggests uncertainty about DB response format. Standardize the DB client return type.

**File:** `khala/application/services/planning_service.py`
**Shame Score:** 85
**Findings:**
* `[Line 50]` **(High)**: Manual JSON extraction (`content.split("```json")`) is brittle. Use `khala.application.utils.parse_json_safely`.
* `[Line 85]` **(Med)**: `verify_plan_logic` assumes LLM returns valid JSON. `json.loads` will raise logic-breaking exception if LLM hallucinates text.

**File:** `khala/application/services/hybrid_search_service.py`
**Shame Score:** 88
**Findings:**
* `[Line 65]` **(Perf)**: `_calculate_proximity_score` uses nested loops `O(N^2)` on term occurrences. Risk of DoS with crafted repetitive documents.
* `[Line 150]` **(Good)**: Parallel execution of Vector and BM25 searches using `asyncio.gather`.
* `[Line 300]` **(High)**: Contextual boosting modifies scores in-place based on magic numbers (`0.2`, `0.1`). These weights should be configurable strategies, not hardcoded.

**File:** `khala/application/services/privacy_safety_service.py`
**Shame Score:** 82
**Findings:**
* `[Line 120]` **(High)**: `sanitize_content` with LLM relies on `_extract_json` (duplicated code).
* `[Line 45]` **(Med)**: `pii_patterns` for credit cards is simplistic (`\d{4}`). It might match non-PII data.

**File:** `khala/infrastructure/executors/cli_executor.py`
**Shame Score:** 90
**Findings:**
* `[Line 35]` **(Good)**: Strict Path Traversal check `startswith(base_path)`.
* `[Line 95]` **(Med)**: Dependence on `npx` and `gemini-mcp-tool` in environment path. Implicit dependency.

**File:** `setup.py`
**Shame Score:** 85
**Findings:**
* `[Line 10]` **(High)**: `surrealdb>=1.0.0` is too loose. Project code uses 2.0 features (`HNSW`). Must lock to `>=2.0.4`.
* `[Line 16]` **(Med)**: `numpy>=2.3.0` likely doesn't exist yet (Typo? 1.23?).

**File:** `khala/application/services/execution_evaluator.py`
**Shame Score:** 0 (BIOHAZARD)
**Findings:**
* `[Line 45]` **(CRITICAL)**: Usage of `exec()` with a naive blacklist is a security catastrophe. Requires `docker` or `firecracker` isolation.

---

## Section 2: The Consolidated Table of Shame

| Severity | File:Line | Error Type | Description | The Fix |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `execution_evaluator.py` | Security | `exec()` usage permits RCE. | DELETE immediately. Use MCP Sandbox. |
| **CRITICAL** | `cli/main.py` | Security | Default password "root". | Remove default. |
| **CRITICAL** | `job_processor.py:158` | Reliability | `json.dumps(payload)` fails on datetime objects. | Use `pydantic.json.pydantic_encoder` or custom serializer. |
| **CRITICAL** | `value_objects.py:28` | Logic | `EmbeddingVector` crashes on unnormalized floats > 1.0. | Relax validation to tolerance (1.0001) or normalize values. |
| **HIGH** | `setup.py:10` | Dependency | `surrealdb` version mismatch (1.0 vs 2.0 code). | Update to `surrealdb>=2.0.4`. |
| **HIGH** | `planning_service.py:50` | Reliability | Brittle manual JSON parsing from LLM. | Use robust JSON parser with retry logic. |
| **HIGH** | `surrealdb/client.py:206` | Integrity | `parse_dt` swallows errors and falsifies timestamps to `now()`. | Raise error on corruption. |
| **MED** | `hybrid_search_service.py:300` | Logic | Hardcoded boosting weights. | Move to configuration/Strategy pattern. |
| **MED** | `privacy_safety_service.py` | Hygiene | Duplicated JSON extraction logic. | Centralize in `utils.py`. |
| **MED** | `cli_executor.py` | Config | Implicit dependency on `npx` in PATH. | Check for tool existence on startup. |
