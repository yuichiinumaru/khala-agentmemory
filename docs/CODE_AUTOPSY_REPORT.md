# FORENSIC CODE AUTOPSY REPORT

**Pathologist:** Senior Engineer Hardcore Code Inquisitor
**Subject:** KHALA Memory System
**Time of Death:** 2025-05-22
**Cause of Death:** Systemic Negligence, Architectural Incompetence, Fake Tests.

---

## SECTION 1: THE FILE-BY-FILE BREAKDOWN

### `khala/infrastructure/surrealdb/client.py`
**Shame Score:** 10/100
**Findings:**
* `[Line 44]` **(Critical)**: `self.password` stores raw secret string. Memory dump vulnerability.
* `[Line 38]` **(High)**: Defaults to `root`/`root` if env vars missing. "Secure by Default" violation.
* `[Line 165]` **(High)**: `create_memory` returns existing ID on hash collision, silently ignoring updates. Logic error (Idempotency vs Update).
* `[Line 120]` **(Med)**: `_deserialize_memory` crashes on invalid enum values. No resilience.
* `[Line 353]` **(Med)**: `_build_filter_query` manually constructs SQL. Injection risk despite regex.

### `khala/infrastructure/gemini/client.py`
**Shame Score:** 15/100
**Findings:**
* `[Line 651]` **(Critical)**: `json.loads(content)` in `analyze_sentiment`. DoS vector via malformed LLM output.
* `[Line 118]` **(High)**: `_complexity_cache` leaks memory (unbounded dict).
* `[Line 157]` **(Med)**: Race condition in `_models` lazy loading.
* `[Line 133]` **(Med)**: Naive complexity heuristic (`count("?")`) allows cost inflation attacks.

### `khala/interface/mcp/server.py`
**Shame Score:** 0/100
**Findings:**
* `[Line 26]` **(Critical)**: Instantiates `SurrealDBClient` with deprecated `url=...` arguments. **Server crashes on startup.**
* `[Line 42]` **(Critical)**: Zero authentication on MCP tools. `analyze_memories` accepts any input.
* `[Line 21]` **(High)**: Hardcoded `root` defaults for DB connection.

### `khala/interface/cli/main.py`
**Shame Score:** 5/100
**Findings:**
* `[Line 192]` **(Critical)**: `surreal-health` command instantiates `SurrealDBClient` with deprecated arguments. **Command crashes.**
* `[Line 126]` **(Med)**: Accesses private method `_get_age_hours` on Memory entity.
* `[Line 85]` **(Nit)**: Uses `asyncio.run` which prevents library usage in existing loops.

### `khala/application/services/memory_lifecycle.py`
**Shame Score:** 30/100
**Findings:**
* `[Line 35]` **(High)**: Instantiates `GeminiClient` in `__init__` default arg logic (potentially). If passed as None, creates new instance.
* `[Line 275]` **(High)**: O(N^2) loop in `deduplicate_memories` (Python-side vector comparison).
* `[Line 353]` **(Med)**: Hardcoded prompt string "Summarize the following...".
* `[Line 390]` **(Med)**: Swallows exceptions in consolidation loop.

### `khala/domain/graph/service.py`
**Shame Score:** 20/100
**Findings:**
* `[Line 25]` **(Critical)**: `getattr(self.repository, 'client', None)` breaks encapsulation and crashes if repo is not `SurrealDBMemoryRepository`.
* `[Line 250]` **(High)**: In-memory graph processing (NetworkX) for centrality/community detection. Will OOM on real data.
* `[Line 200]` **(Med)**: Recursive graph traversal logic relies on specific DB schema function.

### `khala/infrastructure/persistence/audit_repository.py`
**Shame Score:** 40/100
**Findings:**
* `[Line 30]` **(High)**: Silently swallows audit logging failures. "Fail Open" security flaw.

### `khala/infrastructure/executors/cli_executor.py`
**Shame Score:** 5/100
**Findings:**
* `[Line 65]` **(Critical)**: Command Injection via `KHALA_AGENTS_PATH` env var.
* `[Line 73]` **(High)**: Spawns `npx` process for every single task. Performance suicide.

### `khala/application/services/verification_gate.py`
**Shame Score:** 10/100
**Findings:**
* `[Line 270]` **(Critical)**: Calls `db_client.update_memory(memory_id=...)` with invalid signature. Code has never run.
* `[Line 130]` **(High)**: Unbounded `verification_history` list. Memory leak.
* `[Line 260]` **(High)**: Instantiates new `SurrealDBClient` (new pool) for every update. Connection exhaustion.

### `tests/integration/test_novel_strategies.py`
**Shame Score:** 0/100 (Fraudulent)
**Findings:**
* `[Line 77]` **(Critical)**: Fake integration test. Mocks `AsyncSurreal` class to avoid needing a DB, but instantiates `SurrealDBClient` with invalid args. Proves code is broken, yet "passes" via mocking.

### `scripts/verify_creds.py`
**Shame Score:** 0/100
**Findings:**
* `[Line 5]` **(High)**: Brute force tool included in repo.
* `[Line 5]` **(Critical)**: Calls `SurrealDBClient` with invalid args. Script is broken.

### `scripts/check_conn.py`
**Shame Score:** 0/100
**Findings:**
* `[Line 8]` **(Critical)**: Hardcoded `root`/`root` credentials.

### `khala/domain/memory/entities.py`
**Shame Score:** 60/100
**Findings:**
* `[Line 102]` **(Med)**: Hardcoded business rules (promotion thresholds) in Entity.
* `[Line 126]` **(High)**: `__post_init__` validation prevents loading invalid data from DB for repair.

### `khala/debug_intent.py`
**Shame Score:** 0/100
**Findings:**
* `[Line 4]` **(Med)**: Zombie code with hardcoded absolute path `/home/suportesaude/...`.

---

## SECTION 2: THE CONSOLIDATED TABLE OF SHAME

| Severity | File:Line | Error Type | Description | The Fix |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `khala/interface/mcp/server.py:26` | Logic | Server entry point instantiates `SurrealDBClient` with invalid arguments (`url=...`). **Server cannot start.** | Fix `SurrealDBClient` instantiation to use `SurrealConfig`. |
| **CRITICAL** | `khala/interface/cli/main.py:192` | Logic | CLI `surreal-health` command instantiates client with invalid arguments. **Command crashes.** | Update CLI to use `SurrealConfig`. |
| **CRITICAL** | `khala/infrastructure/surrealdb/client.py:44` | Security | `self.password` stores raw secret. | Use `SecretStr`. |
| **CRITICAL** | `khala/domain/graph/service.py:25` | Architecture | GraphService assumes `repository.client` exists. Breaks with decorators/mocks. | Inject `SurrealDBClient` directly or add `get_client()` to interface. |
| **CRITICAL** | `tests/integration/test_novel_strategies.py:77` | Fraud | Fake integration tests hiding broken code. | Delete mocks. Run against Docker. |
| **CRITICAL** | `khala/infrastructure/executors/cli_executor.py:65` | Security | Command Injection via `KHALA_AGENTS_PATH`. | Sanitize paths. |
| **CRITICAL** | `khala/application/services/verification_gate.py:270` | Logic | Calls `update_memory` with invalid signature. | Fix call to match `update_memory(memory)`. |
| **HIGH** | `khala/infrastructure/gemini/client.py:118` | Performance | Memory leak in `_complexity_cache`. | Use `TTLCache`. |
| **HIGH** | `khala/application/services/memory_lifecycle.py:275` | Performance | O(N^2) deduplication in Python. | Move vector distance check to DB. |
| **HIGH** | `khala/infrastructure/persistence/audit_repository.py:30` | Security | Audit failures are swallowed ("Fail Open"). | Raise exception or fallback to safe mode. |
| **HIGH** | `khala/domain/graph/service.py:250` | Performance | In-memory graph processing (NetworkX) on DB data. | Move graph algos to DB or external engine. |
| **MED** | `khala/infrastructure/surrealdb/client.py:120` | Logic | Deserialization crashes on invalid enum. | Add fallback/error handling. |
| **MED** | `khala/infrastructure/surrealdb/client.py:353` | Security | Manual SQL construction in `_build_filter_query`. | Use parameterized queries for everything. |

---

**AUTOPSY CONCLUSION:**
The codebase exhibits a pattern of "Refactoring Scars" where the `SurrealDBClient` signature was changed, but consumers (`server.py`, `cli/main.py`, `tests`, `verification_gate.py`) were never updated. This proves the absence of a working CI/CD pipeline and the falsity of the "Production Ready" claim. The "Integration Tests" are actively deceiving developers by mocking the very components they are supposed to verify.
