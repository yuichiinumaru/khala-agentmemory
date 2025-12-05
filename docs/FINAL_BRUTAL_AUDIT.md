# THE REPORT OF SHAME
**Auditor:** Senior Engineer Hardcore Code Inquisitor
**Target:** Khala Memory System
**Verdict:** FRAGILE. CRITICAL FAILURES IMMINENT.

## Executive Summary
The codebase is a minefield of race conditions, missing methods, and security holes. The `SurrealDBClient` is missing a critical lifecycle method (`close`), guaranteeing crashes in both API and CLI. Privacy handling leaks PII into metadata. Logic for memory promotion is inverted, promoting old junk instead of valuable insights.

## The Violation Table

| Severity | File:Line | Error Type | Description of Failure | The Fix (Ruthless) |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `interface/rest/main.py:59` | Logic / runtime | `await state.db_client.close()` called, but `SurrealDBClient` has no `close()` method. API will crash on shutdown. | Implement `close()` in `SurrealDBClient` to close the pool. |
| **CRITICAL** | `interface/cli/main.py:221` | Logic / runtime | `await client.close()` called in CLI health check. Same missing method crash. | Implement `close()` in `SurrealDBClient`. |
| **CRITICAL** | `app/services/privacy_safety_service.py:78` | Privacy | `redacted_items` metadata potentially stores raw PII returned by LLM if prompt is followed, permanently leaking it. | Validate LLM response. strictly; do NOT store `text` field from PII scan. |
| **CRITICAL** | `infra/surrealdb/client.py:45` | Security | `SurrealConfig` hardcodes `localhost` and `root` credentials as defaults. "Secure by default" violated. | Remove defaults. Force explicit config or fail. |
| **CRITICAL** | `infra/surrealdb/client.py:168` | Logic / Race | `create_memory` calculates hash locally and checks DB. Race condition exists between check and insert. | Add `UNIQUE INDEX` on `content_hash` in DB schema. Handle constraint violation. |
| **CRITICAL** | `interface/rest/main.py:24` | Performance | `get_api_key` calls `os.getenv` on EVERY request. Disk I/O or syscall overhead for no reason. | Load key ONCE at startup into a global constant. |
| **HIGH** | `domain/memory/entities.py:118` | Logic | `should_promote_to_next_tier` promotes Short Term memory if `age > 15 days`. Old junk becomes Long Term automatically. | Invert logic. Old items should decay/archive, not promote unless `importance` is high. |
| **HIGH** | `app/services/memory_lifecycle.py:118` | Logic | `run_lifecycle_job` fetches `limit=1000`. If user has 1001 memories, the last one is never processed (zombie data). | Implement pagination or `scan_all` with cursor. |
| **HIGH** | `infra/gemini/client.py:260` | Logic / Security | `_get_cache_key` truncates MD5 to 16 chars. High collision risk for large corpus. | Use full SHA-256 hash. Storage is cheap, collisions are fatal. |
| **HIGH** | `infra/surrealdb/client.py:326` | Security | `_build_filter_query` uses `params[safe_param_key] = val`. If `val` is a dict/object, behavior is undefined. | Strictly validate `val` types (str, int, float, bool) before passing to DB driver. |
| **MED** | `interface/rest/main.py:38` | Design | Global `state = AppState()` singleton makes testing parallel scenarios impossible. | Use FastAPI `app.state` or Dependency Injection. |
| **MED** | `infra/gemini/client.py:226` | Logic | `input_tokens` estimated as `len * 1.3`. Wildly inaccurate for code/json. Billing will be wrong. | Use `model.count_tokens()` API for accuracy. |
| **MED** | `app/services/memory_lifecycle.py:64` | Performance | `ingest_memory` runs serial blocking awaits (Privacy -> Score -> Sentiment -> Bias). Latency killer. | Use `asyncio.gather` for parallel processing of independent checks. |
| **MED** | `infra/surrealdb/client.py:118` | Concurrency | `_borrow_connection` logic creates new connection if pool empty, ignoring `max_connections` constraint. | Enforce semaphore/limit on total connections, not just pool size. |
| **NIT** | `domain/memory/entities.py:13` | Style | `Memory` entity is mutable (`dataclass` without frozen). Hard to track state changes. | Freeze entities. Use `.replace()` or copy for updates. |
| **NIT** | `infra/surrealdb/client.py:388` | Style | Import `datetime` inside `_deserialize_memory` method. Inefficient. | Move import to module level. |
| **NIT** | `setup.py` | Hygiene | `surrealdb>=1.0.0` specified but code relies on specific async implementation details. | Pin exact version to avoid breaking changes in unstable ecosystem. |

## Conclusion
The project is functional but brittle. The missing `close()` method is a smoking gun indicating lack of integration testing for shutdown/CLI scenarios. The logic errors in promotion and lifecycle management will cause long-term data degradation (infinite promotion of junk, zombie data accumulation). Security posture is "Optimistic" rather than "Zero Trust".

**RECOMMENDATION**: DO NOT DEPLOY without addressing Critical and High issues.
