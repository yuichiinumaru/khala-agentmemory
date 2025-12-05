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

### 💀 Rite of Resurrection: Security Cleanup

**The Rot (Original Sin):**
> *Scripts containing hardcoded credentials left in repository.*

**The Purification Strategy:**
Deleted `scripts/check_conn.py` and `scripts/verify_creds.py`.

-----

**Conclusion:**
The codebase has been purged of its most fatal weaknesses. The architecture now enforces type safety, input validation, and secure defaults.
