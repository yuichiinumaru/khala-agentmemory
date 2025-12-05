# Role: The Senior Engineer Forensic Pathologist (Zero-Mercy Code Autopsy)

**Subject:** KHALA Memory System
**Date:** 2025-12-04
**Status:** CRITICAL CONDITION

## Section 1: The File-by-File Breakdown

### File: `khala/infrastructure/surrealdb/client.py`
**Shame Score:** 20/100
**Findings:**
* `[Line 44]` **(Critical)**: `username="root", password="root"` as default arguments. This is a security catastrophe. The database is wide open by default.
* `[Line 87]` **(High)**: `except Exception as e: logger.debug(...)` inside `initialize`. Database connection failures are swallowed and logged as DEBUG. This makes startup failures invisible.
* `[Line 180]` **(High)**: `hashlib.sha256` is used to generate `content_hash` locally. This logic must match the DB's internal logic exactly or uniqueness checks will drift.
* `[Line 382]` **(Critical)**: `_build_filter_query` manually constructs SQL strings (`f"{key} = ..."`). While it attempts `isalnum()` validation, it is a homemade sanitizer. **SQL Injection Vector**.
* `[Line 539]` **(Med)**: `_deserialize_memory` defaults timestamps to `datetime.now()` if parsing fails. This silently corrupts data provenance.
* `[Line 625]` **(Low)**: `create_search_session` returns `""` (empty string) on failure instead of raising an exception. Caller assumes success.

### File: `khala/infrastructure/gemini/client.py`
**Shame Score:** 35/100
**Findings:**
* `[Line 68]` **(High)**: `_response_cache` is accessed without a lock in `async` methods. Concurrent requests will corrupt the cache dictionary (Race Condition).
* `[Line 68]` **(Med)**: Unbounded cache growth. No `max_size`. Memory leak guaranteed over time.
* `[Line 145]` **(Critical)**: `asyncio.run()` called inside `select_model` which is called by `async generate_text`. **This will crash the event loop** ("asyncio.run() cannot be called from a running event loop").
* `[Line 210]` **(High)**: `generate_text` implements its own exponential backoff retry loop. Use a library like `tenacity` instead of fragile custom logic.
* `[Line 38]` **(Nit)**: `cache_ttl_seconds=300` is a magic number.

### File: `khala/infrastructure/executors/cli_executor.py`
**Shame Score:** 5/100
**Findings:**
* `[Line 16]` **(Critical)**: Hardcoded absolute paths: `/home/suportesaude/YUICHI/...`. This code works ONLY on the developer's machine. It is dead on arrival anywhere else.
* `[Line 87]` **(High)**: `process.wait()` returns the exit code, NOT stdout/stderr. The variables `stdout, stderr` are assigned the result of `wait_for` (which returns the return value of the coro). Effectively, **all output logs are lost**.
* `[Line 68]` **(Med)**: `cmd = ["npx", ...]` relies on external `npx` presence and `gemini-mcp-tool`. Implicit dependency not checked.

### File: `khala/infrastructure/background/jobs/job_processor.py`
**Shame Score:** 40/100
**Findings:**
* `[Line 354]` **(High)**: `_worker_loop` uses polling (`sleep(0.1)`) instead of blocking queue pop (`BLPOP`). High CPU usage for idle workers.
* `[Line 600]` **(High)**: `_handle_job_failure` sleeps (`await asyncio.sleep(delay)`) inside the worker loop. If a job fails, the worker **stops processing all jobs** for 5 minutes. This destroys throughput.
* `[Line 458]` **(Med)**: `_execute_decay_scoring` with `scan_all` loads ALL memory IDs into RAM (`SELECT id FROM memory`). Scale killer.
* `[Line 580]` **(Nit)**: `_execute_job` uses a giant `if/elif` block instead of a dispatch map.

### File: `khala/infrastructure/background/scheduler.py`
**Shame Score:** 60/100
**Findings:**
* `[Line 95]` **(Med)**: `_loop` sleeps for 60 seconds regardless of task interval. A task with `interval=10s` will run effectively randomly every ~60s.
* `[Line 142]` **(Med)**: `create_scheduler` registers tasks with `scan_all: True` which causes the OOM issue in `JobProcessor`.

### File: `khala/infrastructure/persistence/surrealdb_repository.py`
**Shame Score:** 50/100
**Findings:**
* `[Line 90]` **(High)**: `find_duplicate_groups` re-calculates hashes locally (`hashlib.sha256`) instead of trusting the DB's `content_hash`. Redundant and risky.
* `[Line 20]` **(Nit)**: Accesses private member `client._deserialize_memory`. Violation of encapsulation.

### File: `khala/application/services/memory_lifecycle.py`
**Shame Score:** 45/100
**Findings:**
* `[Line 210]` **(High)**: `promote_memories` fetches `limit=1000`. If a user has >1000 memories, old working memories outside this window are **never** promoted.
* `[Line 260]` **(High)**: `deduplicate_memories` performs an O(N^2) comparison loop in Python.
* `[Line 300]` **(Med)**: `schedule_consolidation` hardcodes time-of-day check (`2 <= current_hour <= 5`) assuming UTC server time matches user's preferred maintenance window.

### File: `khala/interface/rest/main.py`
**Shame Score:** 10/100
**Findings:**
* `[Line 16]` **(Critical)**: Global initialization of `db_client` with default credentials. Application starts with insecure defaults.
* `[Line 41]` **(Critical)**: `/metrics` endpoint is unauthenticated. Exposes internal system state to the public.
* `[Line 64]` **(Low)**: `if __name__ == "__main__":` block in library code. Use a separate entry point script.

### File: `khala/interface/mcp/khala_subagent_tools.py`
**Shame Score:** 50/100
**Findings:**
* `[Line 30]` **(Med)**: `session_stats` accumulates indefinitely. Potential memory leak for long-running MCP servers.
* `[Line 200]` **(High)**: Error handling consists of `return {"status": "error"}`. No logging of the actual exception stack trace. Debugging will be impossible.

### File: `khala/domain/memory/entities.py`
**Shame Score:** 70/100
**Findings:**
* `[Line 80]` **(Med)**: Domain logic (`should_promote_to_next_tier`) contains hardcoded magic numbers ("15 days", "0.5 hours"). Should be configurable.
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
| **CRITICAL** | `surrealdb/client.py:44` | Security | Hardcoded `root` credentials. | Require env vars. Fail if missing. |
| **CRITICAL** | `cli_executor.py:16` | Security | Hardcoded absolute paths (`/home/suportesaude...`). | Use relative paths or config. |
| **CRITICAL** | `rest/main.py:41` | Security | Unauthenticated `/metrics` endpoint. | Add Auth middleware. |
| **CRITICAL** | `gemini/client.py:145` | Logic | `asyncio.run` inside async context (Crash). | Use `await`. |
| **CRITICAL** | `surrealdb/client.py:382` | Security | SQL Injection via f-string construction. | Use parameterized queries. |
| **HIGH** | `job_processor.py:600` | Concurrency | Worker sleeps on failure, blocking queue. | Reschedule job, don't sleep worker. |
| **HIGH** | `cli_executor.py:87` | Logic | Logs lost; `wait()` returns exit code. | Use `communicate()`. |
| **HIGH** | `surrealdb/client.py:87` | Reliability | Startup errors swallowed (`logger.debug`). | Raise exceptions on startup. |
| **HIGH** | `gemini/client.py:68` | Concurrency | Race condition on cache access. | Add `asyncio.Lock`. |
| **HIGH** | `memory_lifecycle.py:210` | Logic | Promotion ignores memories beyond limit. | Pagination or iterate all. |
| **HIGH** | `job_processor.py:354` | Perf | Busy-wait polling for jobs. | Use `BLPOP`. |
| **MED** | `scheduler.py:95` | Logic | Scheduler drift due to fixed sleep. | Calculate sleep time. |
| **MED** | `job_processor.py:458` | Perf | Loading all IDs into RAM (`scan_all`). | Use cursor/pagination. |
| **MED** | `surrealdb/client.py:539` | Integrity | Silent timestamp corruption on error. | Raise parsing error. |

**Final Verdict:** The codebase is a "Prototyping Disaster". It works on the developer's machine (`/home/suportesaude`) under low load, but is riddled with security holes, race conditions, and scalability bottlenecks that ensure it will die in production. **Burn it down and rebuild the infrastructure layer.**
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
