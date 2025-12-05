# FORENSIC CODE AUTOPSY REPORT
**Pathologist:** Senior Engineer Forensic Pathologist
**Subject:** Khala Memory System
**Time of Death:** 2025-05-22
**Cause of Death:** Distributed System Organ Failure (Locking, Consistency, Security)

---

## SECTION 1: THE CELLULAR DECOMPOSITION (File-by-File)

### 1. `khala/infrastructure/surrealdb/client.py`
**Shame Score:** 15/100 (Critical Condition)
**Findings:**
*   `[Line 45]` **(Critical)**: `SurrealConfig` defaults to `localhost`/`root`. This is "Insecure by Design".
*   `[Line 68]` **(High)**: `initialize()` swallows connection errors with a log, allowing the app to start in a zombie state.
*   `[Line 168]` **(Critical)**: `create_memory` calculates `content_hash` locally. Race condition: Two clients calculate same hash, both check DB (not found), both insert. Duplicate data.
*   `[Line 326]` **(High)**: `_build_filter_query` accepts generic `value` in dict and assigns to `params`. If value is an object/array not handled by driver, behavior is undefined.
*   `[Line N/A]` **(Critical)**: **MISSING METHOD**: `close()`. The interface layer calls it, but it doesn't exist. Guaranteed crash.
*   `[Line 118]` **(Med)**: `_borrow_connection` creates a new connection if pool is empty, bypassing `max_connections` limit. Connection leak.

### 2. `khala/infrastructure/coordination/distributed_lock.py`
**Shame Score:** 0/100 (Dead on Arrival)
**Findings:**
*   `[Line 38]` **(Critical)**: `CREATE lock SET id = $id` creates a **NEW** record with a random ID every time (unless `lock` table has a specific schema not seen). It does NOT enforce mutual exclusion. `acquire()` always returns True. The entire distributed coordination is a lie.
*   `[Line 34]` **(High)**: `_cleanup_expired` is called before acquire. This creates a race where a valid lock might be deleted if clocks are skewed? No, it deletes *expired* locks. But relying on client-side cleanup is fragile.
*   `[Line 60]` **(Med)**: `release` tries to `DELETE lock WHERE id = $id`. If multiple records were created (due to the bug above), this might delete *all* of them or *none* of them depending on if `$id` matches the property or record ID.

### 3. `khala/infrastructure/persistence/audit_repository.py`
**Shame Score:** 20/100
**Findings:**
*   `[Line 38]` **(Critical)**: **Fail Closed / Data Inconsistency**. If audit logging fails (e.g. DB busy), it raises `RuntimeError`. But the parent operation (e.g. `create_memory`) has *already succeeded*. The action happened, but the audit log claims failure. This is the worst of both worlds.
*   `[Line 21]` **(Nit)**: `CREATE type::thing(...)` syntax is correct, but mixing it with non-transactional logic in the calling service is dangerous.

### 4. `khala/infrastructure/surrealdb/schema.py`
**Shame Score:** 40/100
**Findings:**
*   `[Line N/A]` **(Critical)**: Missing `DEFINE TABLE lock`. Implicit table creation allows the broken distributed lock logic to persist.
*   `[Line 104]` **(High)**: `content_hash_index` is defined but NOT `UNIQUE`. DB allows duplicates, confirming the race condition in `client.py` is unmitigated.
*   `[Line 45]` **(Med)**: `content` field is `TYPE string`. No length limit. DoS vector via massive payload.
*   `[Line 427]` **(Nit)**: RBAC permissions for `owner` check `$auth.user_id`. But the client connects as `root`. These permissions are effectively ghost code.

### 5. `khala/application/services/privacy_safety_service.py`
**Shame Score:** 10/100 (Privacy Violation)
**Findings:**
*   `[Line 78]` **(Critical)**: **PII Leakage**. The code stores `redacted_items` in memory metadata. If the LLM follows the prompt instruction to return `found_pii` with `text`, and the code blindly stores it (or if the `SanitizationResult` is logged), we are permanently persisting the PII we meant to hide.
*   `[Line 131]` **(Med)**: Manual JSON parsing `content.split("```json")`. Extremely fragile. LLMs often chatter before/after JSON.
*   `[Line 30]` **(Med)**: Regex for Email/SSN is simple. False positives likely.

### 6. `khala/domain/memory/entities.py`
**Shame Score:** 60/100
**Findings:**
*   `[Line 118]` **(High)**: **Logic Inversion**. `should_promote_to_next_tier` promotes `SHORT_TERM` to `LONG_TERM` if `age > 15 days`. This means old, ignored garbage is automatically promoted to Long Term memory. It should be the opposite (high importance = promote, low importance = archive).
*   `[Line 27]` **(Nit)**: `Memory` is a mutable `dataclass`. In a concurrent system, passing mutable entities around is asking for race conditions.
*   `[Line 191]` **(Nit)**: `_get_age_hours` relies on `datetime.now(timezone.utc)`. If `created_at` is naive (from bad deserialization), this crashes.

### 7. `khala/infrastructure/gemini/client.py`
**Shame Score:** 50/100
**Findings:**
*   `[Line 260]` **(High)**: `_get_cache_key` truncates MD5 to 16 chars. Birthday paradox says collisions will happen with moderate volume.
*   `[Line 226]` **(Med)**: Token counting is a guess: `len(prompt.split()) * 1.3`. Billing and rate limiting will be inaccurate.
*   `[Line 44]` **(Nit)**: `_response_cache` uses `cachetools` but `_cache_lock` suggests manual thread safety. `cachetools` is not thread-safe, so the lock is good, but complexity is high.

### 8. `khala/interface/rest/main.py`
**Shame Score:** 30/100
**Findings:**
*   `[Line 38]` **(High)**: Global state `state = AppState()`. Hard to test, singleton anti-pattern.
*   `[Line 24]` **(High)**: `get_api_key` calls `os.getenv` on EVERY request. Performance tax.
*   `[Line 59]` **(Critical)**: Calls `state.db_client.close()`. Method does not exist. App crashes on shutdown.

### 9. `khala/interface/cli/main.py`
**Shame Score:** 40/100
**Findings:**
*   `[Line 221]` **(Critical)**: `await client.close()`. Method does not exist. CLI health check crashes.
*   `[Line 80]` **(Nit)**: `_run_async` uses `asyncio.run`. This is fine for CLI but creates a new event loop every time.

### 10. `khala/infrastructure/background/jobs/job_processor.py`
**Shame Score:** 65/100
**Findings:**
*   `[Line 183]` **(Med)**: `_worker_loop` catches `Exception` but not `CancelledError` (in Py<3.8). In Py3.11+ it's fine.
*   `[Line 233]` **(Med)**: `_execute_decay_scoring` fetches `LIMIT 5000` memory IDs if no IDs provided. If system has 1M memories, 99.5% are never decayed.
*   `[Line 110]` **(High)**: `start` initializes `SurrealDBClient()` which might raise `ValueError` (if env missing), crashing the background thread silently or the main app.

---

## SECTION 2: THE CONSOLIDATED TABLE OF SHAME

| Severity | File:Line | Error Type | Description | The Fix |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `infra/coordination/distributed_lock.py:38` | Logic / Security | **Fake Lock**. `CREATE lock SET id=$id` does not enforce uniqueness. Mutual exclusion is broken. | Use `CREATE type::thing('lock', $id)` to target record ID. |
| **CRITICAL** | `infra/surrealdb/client.py:MISSING` | Runtime | **Missing Method**. `close()` is called by API/CLI but not defined. | Implement `close()` to close connection pool. |
| **CRITICAL** | `infra/persistence/audit_repository.py:38` | Consistency | **Audit Fail-Closed**. Logic error causes operation to succeed but throw error if audit fails. | Wrap memory creation + audit in a Transaction. |
| **CRITICAL** | `app/services/privacy_safety_service.py:78` | Privacy | **PII Persistence**. Metadata stores redacted items which may contain raw PII from LLM. | Do not store `text` field from PII scan results. |
| **CRITICAL** | `infra/surrealdb/client.py:45` | Security | **Insecure Defaults**. `SurrealConfig` uses `root`/`root`. | Remove defaults. Require explicit config. |
| **HIGH** | `domain/memory/entities.py:118` | Logic | **Zombie Promotion**. Logic promotes old Short Term memories to Long Term automatically. | Fix logic: Old + Low Importance = Archive. |
| **HIGH** | `infra/surrealdb/schema.py:104` | Data Integrity | **Missing Unique Index**. `content_hash` allows duplicates. | Add `UNIQUE` constraint to `content_hash_index`. |
| **HIGH** | `infra/background/jobs/job_processor.py:233` | Logic | **Partial Processing**. Decay job only processes first 5000 items. | Implement cursor-based pagination (`scan_all`). |
| **HIGH** | `interface/rest/main.py:24` | Performance | **Env Var Polling**. `get_api_key` checks environment on every request. | Load config once at startup. |
| **HIGH** | `infra/gemini/client.py:260` | Security | **Weak Hash**. MD5 truncated to 16 chars for cache keys. | Use SHA-256. |

---

**FINAL VERDICT:**
The codebase is **UNFIT FOR PRODUCTION**. The distributed locking mechanism is fundamentally broken, meaning any feature relying on coordination (consolidation, deduplication) is unsafe. The lack of proper shutdown handling (`close()` missing) and the "Fail-Closed" audit implementation indicate a lack of integration testing. The security posture is performative ("Sanitization" that persists PII).

**IMMEDIATE ACTION REQUIRED:**
1. Fix the Distributed Lock query.
2. Implement Transactions for Audit Logging.
3. Fix the `close()` method crash.
