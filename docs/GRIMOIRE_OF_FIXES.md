# The Grimoire of Fixes
**Author:** The Necromancer
**Date:** 2025-05-22

This document records the resurrection of the Khala codebase. Each entry documents a critical flaw and the "Rite of Resurrection" applied to fix it.

---

### 💀 Rite of Resurrection: `khala/infrastructure/coordination/distributed_lock.py` - Fake Distributed Lock

**The Rot (Original Sin):**
> `CREATE lock SET id = $id` created new records instead of enforcing mutual exclusion. The lock was a placebo.

**The Purification Strategy:**
*   Replaced with `CREATE type::thing('lock', $id)`. This targets the Record ID directly.
*   SurrealDB guarantees Record ID uniqueness. Creation fails if lock exists.

**The Immortal Code:**
```python
q = """
CREATE type::thing('lock', $id) CONTENT {
    expires_at: time::now() + $duration
};
"""
```

---

### 💀 Rite of Resurrection: `khala/infrastructure/surrealdb/client.py` - Missing Lifecycle & Insecure Defaults

**The Rot (Original Sin):**
> Missing `close()` method caused crashes. Defaults allowed insecure `root` access. Race conditions in content hashing allowed duplicates.

**The Purification Strategy:**
*   Implemented `close()` to terminate pools.
*   Enforced explicit `SurrealConfig` validation.
*   Implemented `create_memory` with optimistic creation and duplicate hash recovery (Upsert).

---

### 💀 Rite of Resurrection: `khala/infrastructure/persistence/audit_repository.py` - Fail-Closed Inconsistency

**The Rot (Original Sin):**
> Audit failures raised exceptions *after* memory creation, leaving un-audited data.

**The Purification Strategy:**
*   Wrapped memory creation and audit logging in a database transaction.
*   Refactored `AuditRepository` to accept transaction context.

**The Immortal Code:**
```python
async with self.client.transaction() as conn:
    await self.client.create_memory(..., connection=conn)
    await self.audit_repo.log(..., connection=conn)
```

---

### 💀 Rite of Resurrection: `khala/application/services/privacy_safety_service.py` - PII Leakage

**The Rot (Original Sin):**
> Metadata stored PII returned by the LLM.

**The Purification Strategy:**
*   Updated LLM prompt to ONLY request PII *types*, not the text itself.
*   Hardened JSON parsing logic.

---

### 💀 Rite of Resurrection: `khala/domain/memory/entities.py` - Zombie Promotion

**The Rot (Original Sin):**
> Logic promoted `SHORT_TERM` to `LONG_TERM` based on age (>15 days), effectively promoting garbage.

**The Purification Strategy:**
*   Inverted logic: Promotion now requires High Importance. Age alone leads to Archival.

