"""Audit repository implementation."""
import logging
from typing import Dict, Any
from khala.domain.audit.entities import AuditLog
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class AuditRepository:
    """Repository for storing audit logs."""

    def __init__(self, client: SurrealDBClient):
        self.client = client

    async def log(self, entry: AuditLog) -> str:
        """Record an audit log entry.

        Raises:
            RuntimeError: If audit logging fails. We fail closed for security.
        """
        query = """
        CREATE type::thing('audit_log', $id) CONTENT {
            user_id: $user_id,
            action: $action,
            target_id: $target_id,
            target_type: $target_type,
            details: $details,
            timestamp: $timestamp
        };
        """

        params = entry.to_dict()

        try:
            async with self.client.get_connection() as conn:
                await conn.query(query, params)
            return entry.id
        except Exception as e:
            logger.critical(f"AUDIT FAILURE: Could not record audit log: {e}")
            raise RuntimeError(f"Audit Failure: {e}") from e
