# THE REPORT OF SHAME: BRUTAL CODE AUDIT
**Auditor:** Senior Engineer Hardcore Code Inquisitor (Zero-Mercy)
**Date:** 2025-05-27
**Target:** KHALA Memory System

## Phase 0: Governance & Documentation (FATAL FAILURE)

The project violates the **FORGE** protocols. The `docs/` directory is a graveyard of unorganized markdown files.

| Severity | File | Error Type | Description of Failure | The Fix (Ruthless) |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `docs/` | Governance | Missing strict numbered hierarchy (00-06). Found chaos like `03-architecture-technical.md` instead of `03-architecture.md`. | Rename files to match FORGE spec. Delete orphans. |
| **HIGH** | `AGENTS.md` | Governance | Mentions "Module 15 is missing" but code shows `branch_table`. Inconsistent truth. | Update `AGENTS.md` to reflect reality or delete the ghost code. |
| **MED** | `README.md` | Entropy | Contains architectural details that belong in `03-architecture.md`. | purge `README.md` to a landing page only. |

## Phase 1-4: The Codebase Massacre

| Severity | File:Line | Error Type | Description of Failure | The Fix (Ruthless) |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `khala/interface/cli/main.py` | Security | `password` default value is "root". **Hardcoded credential.** | Remove default. Require env var or prompt. |
| **CRITICAL** | `khala/application/services/execution_evaluator.py` | Security | `exec()` usage. `safe_builtins` is not a sandbox. `forbidden` list is naive. | **DELETE THIS FILE.** Use Docker/Firecracker via MCP. |
| **HIGH** | `khala/infrastructure/surrealdb/client.py:206` | Logic | `parse_dt` swallows errors and returns `now()`. This falsifies memory timestamps. | Raise error. Data integrity > Availability. |
| **HIGH** | `khala/application/services/memory_lifecycle.py` | Logic | `get_by_tier(..., limit=1000)` loop. Creates "zombie memories" if >1000 items exist. | Use pagination (cursor) to process ALL items. |
| **HIGH** | `khala/application/services/memory_lifecycle.py:118` | Reliability | `except Exception` blocks swallow errors silently or with weak logging. | Catch specific exceptions. Fail loudly if critical. |
| **HIGH** | `khala/infrastructure/gemini/client.py` | Security | JSON extraction uses Regex fallbacks. Vulnerable to injection/hallucination. | Use strict JSON mode or schema validation (Pydantic). |
| **MED** | `khala/infrastructure/surrealdb/client.py` | Concurrency | `get_connection` logic with `Semaphore` + `Lock` is complex and prone to deadlocks/races. | Use a battle-tested pool library or simplify. |
| **MED** | `khala/infrastructure/surrealdb/schema.py` | Complexity | `_deserialize_memory` has local imports. Code smell. | Fix circular imports properly at module level. |
| **MED** | `khala/infrastructure/gemini/client.py` | Performance | `_setup_models` calls `genai.configure` globally. | Isolate configuration to the client instance if possible. |
| **NIT** | `khala/interface/rest/main.py` | Hygiene | Global `state` object. | Use FastAPI `app.state` or Dependency Injection. |

## Execution Plan for Remediation

1.  **Purge `execution_evaluator.py`**: It is a security hole.
2.  **Sanitize CLI**: Remove "root" password default.
3.  **Fix Timestamp Logic**: Stop lying about time in `SurrealDBClient`.
4.  **Paginate Lifecycle**: Ensure all memories are processed, not just top 1000.
5.  **Reorganize Docs**: Force alignment with FORGE.

**Signed,**
*The Inquisitor*
