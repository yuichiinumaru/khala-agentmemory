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
**Pathologist:** Senior Engineer Zero-Mercy
**Date:** 2025-12-05
**Subject:** Khala (Codebase)
**Cause of Death:** Multiple Organ Failure (Architecture, Security, Hygiene)

---

## SECTION 1: THE FILE-BY-FILE BREAKDOWN

### 1. `khala/infrastructure/executors/cli_executor.py`
**Shame Score:** 10/100 (CRITICAL CONDITION)
**Findings:**
*   `[Line 53]` **(CRITICAL - Security)**: `cmd = ["npx", ...]`
    *   **Pathology:** You are invoking `npx` implicitly from the shell environment. If an attacker puts a malicious `npx` binary in the path, you are owned.
    *   **The Fix:** Use an absolute path to the node binary or a managed runtime environment.
*   `[Line 91]` **(CRITICAL - DoS)**: `process.communicate()`
    *   **Pathology:** This reads *all* stdout/stderr into memory at once. A malicious tool can output 10GB of zeroes and crash your entire worker node with an OOM.
    *   **The Fix:** Use `asyncio.StreamReader` and process output in chunks.
*   `[Line 32]` **(High - Trust)**: `base_env = os.getenv("KHALA_AGENTS_PATH", "./.gemini/agents")`
    *   **Pathology:** Defaulting to a relative path `.` in a production executor is madness.
    *   **The Fix:** Default to `None` and raise if not set, or use a strict system path like `/opt/khala/agents`.

### 2. `khala/infrastructure/surrealdb/client.py`
**Shame Score:** 40/100 (NECROTIC TISSUE)
**Findings:**
*   `[Line 440]` **(CRITICAL - Data Integrity)**: `if not dt_val: return datetime.now(timezone.utc)`
    *   **Pathology:** You are falsifying history. If a timestamp is missing during deserialization, you invent "now". This corrupts all historical data analytics.
    *   **The Fix:** Raise `ValueError`. Data corruption is worse than a crash.
*   `[Line 183]` **(Critical - Concurrency)**: Client-side `content_hash` check.
    *   **Pathology:** You calculate hash, check if it exists, then write. In a distributed system, two requests will pass the check and you will get duplicates (or DB errors if you are lucky and have a unique index).
    *   **The Fix:** Use an UPSERT or `INSERT IGNORE` strategy at the database level.
*   `[Line 219]` **(High - Fragility)**: `if 'Index' in detail and 'content_hash' in detail:`
    *   **Pathology:** You are parsing error message strings. If SurrealDB updates their error text (e.g., to "Constraint Violation"), your logic breaks silently.
    *   **The Fix:** Check error codes, not strings.
*   `[Line 382]` **(Medium - Hygiene)**: `from khala.domain.memory.entities import Memory...` inside a method.
    *   **Pathology:** Hiding dependencies inside functions is cowardly.
    *   **The Fix:** Fix your circular dependencies properly using `typing.TYPE_CHECKING`.

### 3. `khala/infrastructure/gemini/client.py`
**Shame Score:** 55/100 (INFECTED)
**Findings:**
*   `[Line 328]` **(Medium - Duplication)**: `_extract_json` re-implements regex logic.
    *   **Pathology:** `khala.application.utils.parse_json_safely` exists. You ignored it. Copy-paste coding is cancer.
    *   **The Fix:** Import the utility.
*   `[Line 270]` **(High - Reliability)**: `except Exception as e: logger.error(...)` inside batch loop.
    *   **Pathology:** `generate_embeddings` swallows exceptions. If batch 2 of 10 fails, the caller never knows, but gets a partial list (or nothing?).
    *   **The Fix:** Return a `Result` object with successes and failures, or raise a `BatchError`.
*   `[Line 104]` **(Nitpick)**: `_setup_models` contains `pass`.
    *   **Pathology:** Why does this method exist if it does nothing but side-effects in `try/except`?

### 4. `khala/interface/rest/main.py`
**Shame Score:** 50/100 (ZOMBIE PROCESS)
**Findings:**
*   `[Line 19]` **(High - Performance)**: `os.getenv` on every request.
    *   **Pathology:** You are hitting the OS environment block for every single API call.
    *   **The Fix:** Load configuration once at startup.
*   `[Line 47]` **(Medium - Stability)**: `lifespan` catches startup errors and yields.
    *   **Pathology:** The API starts even if the DB is dead. It serves requests that will inevitably fail 500.
    *   **The Fix:** Let it crash. Kubernetes will restart it. Don't run in a zombie state.

### 5. `khala/application/services/memory_lifecycle.py`
**Shame Score:** 60/100 (AT RISK)
**Findings:**
*   `[Line 183]` **(Performance - Scalability)**: `limit=1000` with no pagination.
    *   **Pathology:** As soon as a user has 1001 memories, the oldest ones become unreachable ghosts.
    *   **The Fix:** Implement cursor-based pagination.
*   `[Line 307]` **(High - Cost)**: Calling `gemini-2.5-pro` inside a loop.
    *   **Pathology:** `consolidate_memories` iterates over groups and calls the LLM sequentially. This is slow and expensive.
    *   **The Fix:** Batch the calls or use `asyncio.gather` (with concurrency limits).
*   `[Line 139]` **(Logic - Distributed Systems)**: Optional Locking.
    *   **Pathology:** "If repository does not expose client; skipping distributed lock". You are allowing race conditions based on implementation details.
    *   **The Fix:** Enforce locking requirements in the interface.

### 6. `khala/domain/sop/services.py`
**Shame Score:** 30/100 (BRAIN DEAD)
**Findings:**
*   `[Line 13]` **(High - Persistence)**: `self._sops: Dict[str, SOP] = {}`
    *   **Pathology:** In-memory storage for a Domain Service. Data dies with the process.
    *   **The Fix:** Inject a Repository.
*   `[Line 24]` **(Performance)**: O(N) linear scan over SOPs.
    *   **Pathology:** `find_sops_by_trigger` loops over every SOP.
    *   **The Fix:** Use an inverted index or a database query.

### 7. `khala/infrastructure/gemini/models.py`
**Shame Score:** 65/100 (CONFUSED)
**Findings:**
*   `[Line 160]` **(High - Type Safety)**: Storing integers as strings (`"0"`).
    *   **Pathology:** `self.model_stats` stores numbers as strings. You are fighting the language.
    *   **The Fix:** Use `int`. Python handles large integers automatically.
*   `[Line 87]` **(Logic)**: `get_embedding_model` returns *any* embedding model.
    *   **Pathology:** Non-deterministic return. You might get 768 dimensions today and 1408 tomorrow.
    *   **The Fix:** Require a `dimensions` or `tier` argument.

### 8. `khala/infrastructure/background/jobs/job_processor.py`
**Shame Score:** 45/100 (PARTIAL)
**Findings:**
*   `[Line 246]` **(Completeness)**: "not_implemented"
    *   **Pathology:** Half the job types return a dummy result.
    *   **The Fix:** Finish the code or remove the dead features.

---

## SECTION 2: THE CONSOLIDATED TABLE OF SHAME

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
| **CRITICAL** | `cli_executor.py:53` | Security (RCE) | Implicit `npx` path execution. | Use absolute paths / runtime managers. |
| **CRITICAL** | `cli_executor.py:91` | Security (DoS) | Unbounded memory buffer for subprocess output. | Use `StreamReader`. |
| **CRITICAL** | `surrealdb/client.py:440` | Data Integrity | Falsifying timestamps (`now()`) on deserialization. | Raise `ValueError`. |
| **CRITICAL** | `surrealdb/client.py:183` | Concurrency | Client-side check-then-act for duplicate hashes. | Database-level constraints/Upsert. |
| **HIGH** | `rest/main.py:19` | Performance | `os.getenv` called on every request. | Load config at startup. |
| **HIGH** | `gemini/client.py:270` | Reliability | Swallowing exceptions in batch operations. | Aggregate errors properly. |
| **HIGH** | `memory_lifecycle.py:307` | Cost/Perf | Sequential LLM calls in loop. | Parallelize with `asyncio.gather`. |
| **HIGH** | `sop/services.py:13` | Persistence | In-memory storage for domain entities. | Use a Repository. |
| **HIGH** | `gemini/models.py:160` | Type Safety | Storing integers as strings in metrics. | Use `int`. |
| **MED** | `gemini/client.py:328` | Hygiene | Duplicated JSON parsing logic. | Import `parse_json_safely`. |
| **MED** | `surrealdb/client.py:382` | Architecture | Local imports hiding circular deps. | Refactor module structure. |
| **MED** | `rest/main.py:47` | Stability | App starts even if DB init fails. | Fail fast (crash). |

**FINAL AUTOPSY VERDICT:**
The patient died of preventable causes. The security holes in `cli_executor.py` are fatal. The data corruption in `surrealdb/client.py` ensures that even if it lived, it would have no memory. Recommendation: **Resuscitate only after major surgery.**
