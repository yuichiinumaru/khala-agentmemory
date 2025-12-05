# HOSTILE CODE AUDIT REPORT (V2)

**Auditor:** Senior Engineer Hardcore Code Inquisitor (Zero-Mercy)
**Date:** 2025-05-22
**Target:** KHALA Memory System
**Verdict:** **UNFIT FOR PRODUCTION**

## Executive Summary

The codebase is a minefield of security vulnerabilities, critical logic errors, and architectural hallucinations. The documentation claims "Production Ready" status, which is a fraudulent statement. The system is riddled with hardcoded credentials, broken tests, memory leaks, and command injection vectors. The "Integration Tests" are a complete fabrication, testing only mocks against mocks.

The system requires immediate, catastrophic refactoring before it can be trusted with a single byte of real data.

## The Table of Shame

| Severity | File:Line | Error Type | Description of Failure | The Fix (Ruthless) |
| :--- | :--- | :--- | :--- | :--- |
| **CRITICAL** | `khala/infrastructure/surrealdb/client.py:44` | Security | Hardcoded credentials in memory. `self.password` stores the raw secret string, exposing it to memory dumps and debuggers. | Use `SecretStr` throughout and never store plain text. |
| **CRITICAL** | `scripts/check_conn.py:8` | Security | Hardcoded `root`/`root` credentials. Committing this to the repo guarantees accidental leakage or misuse against production. | Delete the script. Use env vars only. |
| **CRITICAL** | `tests/integration/test_novel_strategies.py:77` | Fraud | **Fake Integration Tests.** The test creates a `SurrealDBClient` with invalid arguments (`url=...`) which should crash, but it passes because it mocks everything including the class itself. It tests NOTHING. | Delete the file. Write real integration tests against a Dockerized DB. |
| **CRITICAL** | `khala/infrastructure/executors/cli_executor.py:65` | Security | **Command Injection.** `agent_file` is derived from `KHALA_AGENTS_PATH`. If attacker controls env, they execute arbitrary files. | Validate paths against an allowlist. Use `safe_join`. |
| **CRITICAL** | `khala/infrastructure/gemini/client.py:651` | Security | **Vulnerable JSON Parsing.** `json.loads(content)` in `analyze_sentiment` will crash on markdown output. Denial of Service vector. | Use a robust JSON extractor or a structured output parser. |
| **CRITICAL** | `khala/application/services/verification_gate.py:270` | Logic | **Invalid Method Call.** Calls `db_client.update_memory(memory_id=...)` but the method signature requires a `Memory` object. This code has never been run. | Fix the signature or the call. Write a REAL test. |
| **HIGH** | `khala/infrastructure/surrealdb/client.py:165` | Logic | **Silent Failure on Create.** `create_memory` returns existing ID if hash collision found, ignoring any updates/changes. Idempotency without verification is dangerous. | Update the existing record or raise `ConflictError`. |
| **HIGH** | `khala/infrastructure/gemini/client.py:118` | Performance | **Memory Leak.** `_complexity_cache` grows indefinitely with every unique prompt. A long-running service will OOM. | Use `TTLCache` or `LRUCache`. |
| **HIGH** | `khala/infrastructure/executors/cli_executor.py:73` | Performance | **Process Spawning Hell.** Spawns `npx` (Node.js) for *every single subagent task*. This will destroy CPU/Latency under load. | Use a persistent server/worker or native Python implementation. |
| **HIGH** | `khala/interface/rest/main.py:69` | Security | **Auth Bypass.** `/health` endpoint executes DB query (`RETURN true`) without auth. DDoS vector to exhaust DB pool. | Rate limit the endpoint or remove the DB query. |
| **HIGH** | `khala/domain/memory/entities.py:126` | Logic | **Crash on Invalid Data.** `__post_init__` validation raises `ValueError` on read. If DB contains bad data, the app crashes and cannot read it to fix it. | Validate on WRITE, be lenient on READ. |
| **HIGH** | `scripts/verify_creds.py:5` | Security | **Brute Force Tool.** Script designed to brute-force DB credentials included in source. Useful for attackers, dangerous for insiders. | Delete the file. |
| **MED** | `khala/infrastructure/gemini/client.py:133` | Logic | **Naive Complexity Heuristic.** `prompt.count("?")` is easily gameable. Attacker can force expensive models by appending junk. | Use a fast LLM or robust tokenizer for classification. |
| **MED** | `khala/infrastructure/surrealdb/client.py:353` | Security | **Potential SQL Injection.** `_build_filter_query` constructs SQL strings. While keys are regex-validated, it's brittle. | Use parameterized queries for EVERYTHING, including keys if possible (Surreal restriction). |
| **MED** | `khala/interface/rest/main.py:26` | Security | **Timing Attack.** `api_key_header == expected_key` is not constant-time. | Use `secrets.compare_digest`. |
| **MED** | `khala/infrastructure/gemini/client.py:157` | Concurrency | **Race Condition.** `_models` lazy initialization is not thread-safe. Multiple requests can trigger parallel initialization. | Use `asyncio.Lock` for model initialization. |
| **MED** | `khala/debug_intent.py:4` | Hygiene | **Zombie Code.** Hardcoded path `/home/suportesaude/...`. Imports non-existent module? | Delete the file. |
| **MED** | `setup.py:12` | Config | **Dependency Mismatch.** Requires `google-genai` but code uses `google.generativeai`. | Fix `install_requires` to match actual imports. |
| **NIT** | `khala/domain/memory/entities.py:102` | Logic | **Hardcoded Business Rules.** Promotion logic (15 days, etc.) buried in Entity. | Move rules to a `Policy` or `Configuration` object. |
| **NIT** | `khala/infrastructure/surrealdb/client.py:38` | Config | **Insecure Default.** Defaults to `root`/`root` if env vars missing. | Raise error if auth not provided. Secure by Default. |

## Detailed Analysis

### 1. The "Fake Test" Scandal
The project relies on `tests/integration/test_novel_strategies.py` and `tests/brutal/conftest.py` which implement a **Mock Object** that swallows all queries.
- `MockAsyncSurreal.query` returns hardcoded success responses.
- The tests verify that the *Python code calls the mock*, not that the code works with SurrealDB.
- **Evidence:** The tests instantiate `SurrealDBClient(url=...)` which uses a deprecated signature. In a real environment, this would raise `TypeError` immediately. The tests pass because they patch the class itself.

### 2. Security Theatre
- **Secrets:** Passwords are stored in plain text in `self.password` attributes. Scripts like `check_conn.py` and `verify_creds.py` are left in the repo with default `root` credentials.
- **Validation:** The `verification_gate.py` service, intended to ensure quality, crashes because it calls a non-existent method signature (`update_memory(memory_id=...)`). It has clearly never been run against the actual code.

### 3. Performance & Stability
- **Memory Leaks:** `GeminiClient` caches complexity scores forever.
- **Process Spawning:** `CLIExecutor` runs `npx` for every task. This is acceptable for a prototype, but fatal for a "Production Ready" system.
- **Connection Pools:** `VerificationGate` instantiates a *new* `SurrealDBClient` (and thus a new pool) for *every* memory update. This ensures rapid resource exhaustion.

## Conclusion

This codebase is a prototype masquerading as a production system. It requires a complete audit of every single service method to ensure it matches the infrastructure layer's actual API. Security practices are non-existent.

**Recommendation:** Do not deploy. Revoke all API keys. Rewrite tests to use a real Dockerized SurrealDB instance.
