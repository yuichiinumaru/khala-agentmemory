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
*   `[Line 307]` **(High - Cost)**: Calling `gemini-3-pro-preview` inside a loop.
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
