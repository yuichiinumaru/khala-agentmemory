# 09-SECURITY.md: Security Architecture

**Project**: KHALA v2.0
**Reference**: [04-database-schema.md](04-database-schema.md)

---

## 1. Zero Trust Principles

*   **Verify Explicitly**: Every API call must be authenticated.
*   **Least Privilege**: Agents only access their own namespace.
*   **Assume Breach**: Data is encrypted; logs are immutable.

---

## 2. Authentication & Authorization

### API Access
*   **Internal**: No Auth (runs in same process).
*   **MCP/REST**: Bearer Token (JWT).

### Database Access (RBAC)
SurrealDB handles security at the record level.

```surrealql
-- Only allow users to see their own memories
DEFINE TABLE memory SCHEMAFULL
    PERMISSIONS
        FOR select, create, update, delete
        WHERE user_id = $auth.id;
```

---

## 3. Data Protection

*   **At Rest**: SurrealDB runs on encrypted volumes (LUKS/EBS Encrypted).
*   **In Transit**: TLS 1.3 enforced for all connections (WSS/HTTPS).
*   **Sanitization**: Input sanitization to prevent Injection attacks.

---

## 4. Audit Logging

*   **Immutable Logs**: `audit_log` table is append-only.
*   **Scope**: Records Actor, Action, Target, and Timestamp.
*   **Retention**: 1 year.

---

## 5. Compliance

*   **GDPR**: Support "Right to be Forgotten" via `DELETE` cascading.
*   **Data Portability**: Full export via JSON.
