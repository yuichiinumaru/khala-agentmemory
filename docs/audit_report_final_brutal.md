# Role: The Senior Engineer Hardcore Code Inquisitor (Zero-Mercy Auditor)

**Status:** BRUTAL AUDIT COMPLETE
**Date:** 2025-12-05
**Verdict:** **UNACCEPTABLE**

---

## Phase 0: The Bureaucratic Purge (Governance & Documentation)

The project violates the **FORGE v2 Protocol** in multiple areas.

| Violation Type | File/Path | Description | The Fix |
| :--- | :--- | :--- | :--- |
| **Illegal Artifact** | `docs/` | Found files outside the canonical sequence: `api-integration.md`, `strategies.md`, `database-schema.md`. | **DELETE or RENAME** to follow `NN-name.md` format. |
| **Zombie Docs** | `docs/` | Orphaned reports: `CODE_AUDIT_REPORT.md`, `CODE_AUDIT_REPORT_V2.md`, etc. | **MOVE** to `docs/_archive/` immediately. |
| **Loose Governance** | `docs/03-codebase-assessment.md` | Breaks the numbered sequence. | **MERGE** into `00-draft.md` or `01-plan.md`. |
| **Entropy** | `tests/` | Found non-standard test roots: `brutal/`, `resurrection/`. | **CONSOLIDATE** into `unit/`, `integration/`. |

---

## The Table of Shame (Code Findings)

| Severity | File:Line | Error Type | Description of Failure | The Fix (Ruthless) |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `khala/infrastructure/executors/cli_executor.py:53` | **Security (RCE)** | Implicit reliance on `npx` in shell command (`cmd = ["npx", ...]`). Vulnerable to PATH hijacking. | Use absolute path for `npx` or invoke via managed node runtime. |
| **CRITICAL** | `khala/infrastructure/executors/cli_executor.py:91` | **Stability (DoS)** | `process.communicate()` buffers all output in memory. Malicious tool can OOM the service. | specific `asyncio.StreamReader` with chunks. |
| **HIGH** | `khala/infrastructure/surrealdb/client.py:440` | **Data Integrity** | `parse_dt` defaults to `now()` when timestamp is missing/invalid. **This corrupts historical data.** | Raise `ValueError`. If data is missing, the write is invalid. |
| **HIGH** | `khala/interface/rest/main.py:19` | **Performance** | `get_api_key` calls `os.getenv` on **every single request**. IO overhead for auth. | Load config ONCE at startup into `AppState`. |
| **HIGH** | `khala/infrastructure/gemini/client.py:270` | **Reliability** | `generate_embeddings` swallows exceptions in batch loop (`except Exception as e: logger.error...`). Data loss is silent. | Aggregate errors and return partial success or fail the whole batch loudly. |
| **MED** | `khala/infrastructure/surrealdb/client.py:382` | **Architecture** | `_deserialize_memory` contains local imports (`from ... entities`). Hides circular deps. | Refactor `entities.py` to break cycles or use `TYPE_CHECKING`. |
| **MED** | `khala/domain/memory/entities.py:100` | **Logic** | `__post_init__` "Self-Healing" resets negative values (e.g. `access_count`). Masks logic bugs elsewhere. | Raise `ValueError`. Do not hide upstream bugs. |
| **MED** | `khala/interface/rest/main.py:47` | **Stability** | `lifespan` catches startup exceptions and `yields`. API starts in "Zombie Mode" (no DB). | Raise `RuntimeError` and crash the container. Fail fast. |
| **MED** | `khala/infrastructure/gemini/client.py:328` | **Duplication** | `_extract_json` re-implements fragile regex logic found in `khala/application/utils.py`. | **Import `parse_json_safely`** from utils. DRY violation. |
| **LOW** | `khala/infrastructure/surrealdb/client.py:126` | **Concurrency** | `_borrow_connection` accepts optional `connection` but bypasses semaphore tracking. | Ensure borrowed connections are tracked or explicitly untracked. |
| **LOW** | `khala/infrastructure/background/jobs/job_processor.py:246` | **Completeness** | Multiple jobs (`deduplication`, `consistency_check`) return "not_implemented". | Implement them or remove the job types. |

---

## Phase 4: Chaos Simulation Results

1.  **"What if the database is down?"**
    *   API starts anyway (`lifespan` swallows error).
    *   Health check returns 503 (Correct).
    *   **Verdict**: Partial Failure. The service should not start.

2.  **"What if the LLM returns garbage JSON?"**
    *   `GeminiClient` has fragile regex.
    *   `PlanningService` uses `parse_json_safely` (Good).
    *   **Verdict**: Inconsistent.

3.  **"What if I inject a command?"**
    *   `CLIExecutor` checks for `..` in paths (Good).
    *   But relies on system `npx`.
    *   **Verdict**: VULNERABLE.

---

**Final Instruction:**
The codebase is **REJECTED**.
Immediate remediation of CRITICAL and HIGH issues is mandatory before any feature work.
