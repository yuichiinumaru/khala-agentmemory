# THE GRIMOIRE OF FIXES
**Necromancer:** Senior Engineer Necromancer
**Phase:** 3.2 - Code Purification
**Status:** COMPLETED

---

## 💀 Rite 1: Purge ExecutionEvaluator [Security-Critical]

**The Rot:**
> `exec(code, ...)`
> Naive blacklist in `ExecutionEvaluator` allowed RCE.

**The Fix:**
*   Deleted `khala/application/services/execution_evaluator.py`.
*   Cleaned `khala/tests/unit/application/test_phase2_services.py`.
*   **Strategy:** Zero Trust. No unsafe execution in core.

## 💀 Rite 2: Relax Vector Validation [Logic-Critical]

**The Rot:**
> `if not (-1 <= value <= 1): raise ValueError`
> Strict bounds checking caused crashes with unnormalized vectors from certain models.

**The Fix:**
*   Updated `khala/domain/memory/value_objects.py`.
*   Added `tolerance = 1e-4`.
*   **Strategy:** Robustness Principle (Postel's Law).

## 💀 Rite 3: Robust Job Serialization [Reliability-Critical]

**The Rot:**
> `json.dumps(job.payload)`
> Crashed when payload contained `datetime` objects.

**The Fix:**
*   Created `khala/application/utils.py` with `json_serializer`.
*   Updated `khala/infrastructure/background/jobs/job_processor.py` to use `default=json_serializer`.
*   **Strategy:** Fail Safe.

## 💀 Rite 4: Secure CLI Defaults [Security-Critical]

**The Rot:**
> `default="root"` for DB password in CLI.

**The Fix:**
*   Updated `khala/interface/cli/main.py`.
*   Removed defaults, added `required=True` and `envvar` support.
*   **Strategy:** Secure by Design.

## 💀 Rite 5: Fail-Loud Timestamp Parsing [Data-Integrity]

**The Rot:**
> `except ValueError: return datetime.now()`
> Silently swallowed errors and falsified data timestamps.

**The Fix:**
*   Updated `khala/infrastructure/surrealdb/client.py`.
*   Changed to raise `ValueError` on corruption.
*   **Strategy:** Fail Loudly.

## 💀 Rite 6: Robust JSON Extraction [Reliability]

**The Rot:**
> Manual regex parsing duplicated across services. Brittle to LLM output variations.

**The Fix:**
*   Implemented `parse_json_safely` in `khala/application/utils.py`.
*   Refactored `PlanningService` and `PrivacySafetyService` to use it.
*   **Strategy:** DRY (Don't Repeat Yourself).

## 💀 Rite 7: Dependency Hell [Config]

**The Rot:**
> `surrealdb>=1.0.0` (incompatible with v2 code).
> `numpy>=2.3.0` (non-existent).

**The Fix:**
*   Updated `setup.py` to pin `surrealdb>=2.0.4` and `numpy>=1.26.0`.
*   **Strategy:** Explicit Dependencies.
