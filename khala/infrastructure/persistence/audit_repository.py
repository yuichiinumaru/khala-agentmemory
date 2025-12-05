"""Audit repository implementation."""
import logging
from typing import Optional, Any
try:
    from surrealdb import AsyncSurreal
except ImportError:
    pass

from khala.domain.audit.entities import AuditLog
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class AuditRepository:
    """Repository for storing audit logs."""

    def __init__(self, client: SurrealDBClient):
        self.client = client

    async def log(self, entry: AuditLog, connection: Optional["AsyncSurreal"] = None) -> str:
        """
        Record an audit log entry.

        Args:
            entry: The audit log entity.
            connection: Optional existing connection for transactions.

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

        # Use helper from client to manage connection borrowing
        # But here we are in a separate class.
        # Ideally we use self.client._borrow_connection(connection)
        # But _borrow_connection is protected (single underscore).
        # We can respect the API or access it if we consider this infra package internal.
        # Or we implement the logic here.

        try:
            if connection:
                await connection.query(query, params)
            else:
                async with self.client.get_connection() as conn:
                    await conn.query(query, params)
            return entry.id
        except Exception as e:
            logger.critical(f"AUDIT FAILURE: Could not record audit log: {e}")
            raise RuntimeError(f"Audit Failure: {e}") from e
