# The Grimoire of Fixes (The Rite of Resurrection)

**Necromancer:** Senior Architect Jules
**Date:** 2025-12-04

---

## 💀 Rite of Resurrection: `khala/infrastructure/surrealdb/client.py` - Security & Stability

**The Rot (Original Sin):**
> `username="root", password="root"` as default arguments. `except Exception as e: logger.debug(...)` swallowing connection errors. SQL Injection via `f"{key} = ..."`.

**The Purification Strategy:**
Replaced hardcoded defaults with `pydantic.BaseSettings` (via `SurrealConfig`) that loads from environment variables and **crashes immediately** if `SURREAL_PASS` is missing. Removed exception swallowing to ensure "Fail Loudly". Rewrote query builder to use parameterized queries (`$filter_param`) with hashed keys to prevent collision.

**The Immortal Code:**
```python
class SurrealConfig(BaseModel):
    # ...
    @classmethod
    def from_env(cls) -> "SurrealConfig":
        password = os.getenv("SURREAL_PASS")
        if not password:
             raise ValueError("CRITICAL: SURREAL_PASS environment variable is missing. Startup aborted.")
        return cls(..., password=SecretStr(password))

# Parameterized Query with Collision Safety
key_hash = hashlib.md5(key.encode()).hexdigest()[:8]
safe_param_key = f"filter_{key_hash}"
params[safe_param_key] = value
clauses.append(f"{key} = ${safe_param_key}")
```

**Verification Spell:**
Run `scripts/verify_creds.py` without env vars; verify it fails with exit code 1.

---

## 💀 Rite of Resurrection: `khala/infrastructure/gemini/client.py` - Concurrency & Leaks

**The Rot (Original Sin):**
> `asyncio.run()` called inside `select_model` (async context crash). Unbounded `_response_cache` dictionary (Memory Leak). Race conditions on cache access.

**The Purification Strategy:**
Refactored `select_model` to be fully `async` and awaited it. Replaced raw dict cache with `cachetools.TTLCache` (LRU + Time-based eviction). Added `asyncio.Lock` for thread-safe cache access.

**The Immortal Code:**
```python
import cachetools

# ...
self._response_cache = cachetools.TTLCache(maxsize=1000, ttl=cache_ttl_seconds)
self._cache_lock = asyncio.Lock()

async def _cache_response(self, key, data):
    async with self._cache_lock:
        self._response_cache[key] = data
```

**Verification Spell:**
Run `tests/brutal/test_concurrency.py` to verify no event loop crashes or cache corruption under load.

---

## 💀 Rite of Resurrection: `khala/infrastructure/executors/cli_executor.py` - Portability

**The Rot (Original Sin):**
> Hardcoded absolute paths `/home/suportesaude/...`. Logs lost due to `process.wait()`.

**The Purification Strategy:**
Used `os.getenv("KHALA_AGENTS_PATH")` for dynamic configuration. Replaced `process.wait()` with `process.communicate()` to capture and log stdout/stderr.

**The Immortal Code:**
```python
base_path = os.getenv("KHALA_AGENTS_PATH", "./.gemini/agents")
stdout, stderr = await process.communicate()
if process.returncode != 0:
    logger.error(f"Subagent CLI failed: {stderr}")
```

**Verification Spell:**
Run CLI executor in a container (different path); verify it finds agents via env var. Check logs for subagent errors.

---

## 💀 Rite of Resurrection: `khala/interface/rest/main.py` - Security

**The Rot (Original Sin):**
> Global `db_client` init. Unauthenticated `/metrics`.

**The Purification Strategy:**
Implemented `lifespan` context manager for proper startup/shutdown. Added `get_api_key` dependency to endpoints.

**The Immortal Code:**
```python
def get_api_key(api_key: str = Security(...)):
    if not match: raise HTTPException(403)

@app.get("/metrics", dependencies=[Depends(get_api_key)])
async def get_metrics(): ...
```

**Verification Spell:**
`curl -I http://localhost:8000/metrics` should return 403 Forbidden.

---

## 💀 Rite of Resurrection: `khala/infrastructure/background/jobs/job_processor.py` - Robustness

**The Rot (Original Sin):**
> Busy-wait polling. Worker sleeps on failure (blocking queue). `scan_all` loads all IDs into RAM.

**The Purification Strategy:**
Implemented adaptive sleep for idle workers. Changed failure handling to re-queue with `scheduled_at` (non-blocking). Added safety limit to `scan_all`.

**The Immortal Code:**
```python
# Adaptive Sleep
if not job: await asyncio.sleep(1.0)

# Non-blocking Retry
asyncio.create_task(re_queue())
# OR use scheduled_at if supported by backend
```

**Verification Spell:**
Submit a failing job; verify other jobs continue processing immediately. Submit `scan_all`; verify RAM usage is stable.
