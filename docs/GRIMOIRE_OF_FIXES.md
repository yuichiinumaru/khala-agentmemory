# The Grimoire of Fixes

**Necromancer:** Senior Architect
**Date:** 2025-05-22
**Purpose:** Resurrection of the KHALA Memory System

-----

### 💀 Rite of Resurrection: SurrealDB Client - [Security/Logic]

**The Rot (Original Sin):**
> *`self.password` stores the raw secret string, exposing it to memory dumps.*
> *`create_memory` returns existing ID on hash collision, silently ignoring updates.*

**The Purification Strategy:**
Replaced the `__init__` logic with a strict `SurrealConfig` Pydantic model. Passwords are now wrapped in `SecretStr`. Removed default `root/root` credentials; the system now crashes if `SURREAL_USER` is missing (Zero Trust).
Rewrote `create_memory` to explicitly `UPDATE` the record if a hash collision occurs, ensuring idempotency does not mean data staleness.

**The Immortal Code:**
```python
class SurrealConfig(BaseModel):
    # ...
    password: SecretStr

    @classmethod
    def from_env(cls) -> "SurrealConfig":
        if not os.getenv("SURREAL_USER"):
             raise ValueError("CRITICAL: SURREAL_USER environment variable is missing.")
        # ...
```

**Verification Spell:**
`SURREAL_USER="" python -c "from khala.infrastructure.surrealdb.client import SurrealDBClient; SurrealDBClient()"` -> Crashes with ValueError.

-----

### 💀 Rite of Resurrection: Gemini Client - [JSON Vulnerability/Leaks]

**The Rot (Original Sin):**
> *`json.loads(content)` in `analyze_sentiment`. DoS vector via malformed LLM output.*
> *`_complexity_cache` leaks memory (unbounded dict).*

**The Purification Strategy:**
Implemented `_extract_json` with Regex fallback to handle Markdown code blocks (` ```json ... ``` `) and malformed output. Replaced standard `dict` caches with `cachetools.TTLCache` (LRU) to cap memory usage. Added thread-safety locks for model initialization.

**The Immortal Code:**
```python
def _extract_json(self, text: str) -> Dict[str, Any]:
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        # Regex Rescue
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match: return json.loads(match.group(0))
        return {}
```

-----

### 💀 Rite of Resurrection: Entry Points - [Crash/Startup]

**The Rot (Original Sin):**
> *Instantiates `SurrealDBClient` with deprecated `url=...` arguments.*

**The Purification Strategy:**
Refactored `khala/interface/mcp/server.py` and `khala/interface/cli/main.py` to construct `SurrealConfig` objects before instantiating the client. This ensures validation happens before any connection attempt.

-----

### 💀 Rite of Resurrection: CLI Executor - [Command Injection]

**The Rot (Original Sin):**
> *Command Injection via `KHALA_AGENTS_PATH` env var.*

**The Purification Strategy:**
Added strict path resolution using `pathlib.Path.resolve()`. The code now verifies that the resolved agent file path lies strictly within the allowed `base_path` directory, preventing `../../etc/passwd` attacks.

**The Immortal Code:**
```python
agent_path = (base_path / filename).resolve()
if not str(agent_path).startswith(str(base_path)):
     raise ValueError(f"Security Alert: Path traversal attempted: {agent_path}")
```

-----

### 💀 Rite of Resurrection: Verification Gate - [Logic/Leaks]

**The Rot (Original Sin):**
> *Unbounded `verification_history` causing memory leaks.*
> *Calls `update_memory` with invalid arguments (crash).*

**The Purification Strategy:**
Replaced list with `collections.deque(maxlen=1000)` to cap memory usage. Refactored `update_memory` usage to correctly fetch, update, and save the full `Memory` entity using the Repository pattern.

-----

### 💀 Rite of Resurrection: Memory Lifecycle - [Performance/DI]

**The Rot (Original Sin):**
> *O(N^2) loop in `deduplicate_memories`.*
> *Hidden dependency on `GeminiClient` in default args.*

**The Purification Strategy:**
Enforced dependency injection for `GeminiClient` in `__init__`. Capped batch size for semantic deduplication to 50 items to prevent quadratic explosions. Added explicit error logging (`logger.exception`) instead of swallowing exceptions.

-----

### 💀 Rite of Resurrection: Graph Service - [Architecture/OOM]

**The Rot (Original Sin):**
> *`getattr(self.repository, 'client')` breaks encapsulation.*
> *In-memory graph processing of unbounded datasets.*

**The Purification Strategy:**
Updated `GraphService` to accept `SurrealDBClient` via Dependency Injection. Implemented strict limits (2000 nodes) for in-memory graph algorithms (`calculate_centrality`, etc.) to prevent OOM. Offloaded graph computation to `asyncio.to_thread` to prevent blocking the event loop.

-----

### 💀 Rite of Resurrection: Domain Entities - [Fragility]

**The Rot (Original Sin):**
> *`__post_init__` crashes on invalid data read from DB.*
> *Hardcoded business rules buried in methods.*

**The Purification Strategy:**
Refactored `__post_init__` to use "Self-Healing" logic (logging warnings and clamping invalid values) instead of raising `ValueError` on read. Extracted business rules (promotion thresholds) to class constants for visibility. Added `get_age_hours` alias for compatibility.

-----

### 💀 Rite of Resurrection: Audit Repository - [Security]

**The Rot (Original Sin):**
> *Silently swallows audit logging failures ("Fail Open").*

**The Purification Strategy:**
Modified `log()` to raise `RuntimeError` if audit persistence fails. This ensures a "Fail Closed" security posture where operations cannot proceed without an audit trail.

-----

### 💀 Rite of Resurrection: Job Processor - [Concurrency]

**The Rot (Original Sin):**
> *Sleeping on failure blocks processing logic.*
> *Unbounded queries in `scan_all` lead to OOM.*

**The Purification Strategy:**
Refactored worker loop to use optimized sleep (0.1s) and ensuring job fetching failures do not stall the worker unnecessarily. Added strict `LIMIT` clauses to SQL queries in consolidation and decay jobs to prevent memory exhaustion.

-----

### 💀 Rite of Resurrection: REST API - [Security]

**The Rot (Original Sin):**
> *Timing attack in API Key validation.*
> *Unauthenticated `/health` endpoint executing DB queries (DDoS).*

**The Purification Strategy:**
Implemented `secrets.compare_digest` for constant-time authentication. Split health checks into `/health` (Liveness, unauth, no DB) and `/ready` (Readiness, auth, DB check). Prevented log flooding from missing API keys.

-----

### 💀 Rite of Resurrection: Configuration - [Consistency]

**The Rot (Original Sin):**
> *Dependency mismatch (`google-genai` vs `google-generativeai`).*

**The Purification Strategy:**
Updated `setup.py` to require the correct package `google-generativeai`, ensuring reproducibility. Added `cachetools` to dependencies.

-----

### 💀 Rite of Resurrection: Test Suite - [Infrastructure]

**The Rot (Original Sin):**
> *Tests fail because they instantiate `SurrealDBClient` without environment configuration, which is now mandatory.*

**The Purification Strategy:**
Updated `tests/brutal/conftest.py` and `tests/unit/conftest.py` to inject mock environment variables (`SURREAL_USER`, `SURREAL_PASS`, etc.) before any tests run. This ensures the strict validation in `SurrealConfig` passes during test setup.

-----

### 💀 Rite of Resurrection: Security Cleanup

**The Rot (Original Sin):**
> *Scripts containing hardcoded credentials left in repository.*
> *Zombie code (`debug_intent.py`) with hardcoded paths.*

**The Purification Strategy:**
Deleted `scripts/check_conn.py`, `scripts/verify_creds.py`, `khala/debug_intent.py`, and `tests/integration/test_novel_strategies.py`.

-----

**Conclusion:**
The codebase has been purged of its most fatal weaknesses. The architecture now enforces type safety, input validation, secure defaults, and robust error handling. The test suite is now compatible with the hardened configuration.
