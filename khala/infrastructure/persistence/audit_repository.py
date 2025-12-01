"""Audit repository implementation."""
import logging
from typing import Dict, Any, List
from datetime import datetime
from khala.domain.audit.entities import AuditLog
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class AuditRepository:
    """Repository for storing audit logs."""

    def __init__(self, client: SurrealDBClient):
        self.client = client

    async def log(self, entry: AuditLog) -> str:
        """Record an audit log entry."""
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
            logger.error(f"Failed to record audit log: {e}")
            # We don't raise here to prevent audit failure from blocking main operation,
            # but in strict compliance mode, we might want to.
            return ""

    async def get_logs_by_target(self, target_id: str) -> List[AuditLog]:
        """Retrieve audit logs for a specific target."""
        query = """
        SELECT * FROM audit_log
        WHERE target_id = $target_id
        ORDER BY timestamp ASC;
        """

        try:
            async with self.client.get_connection() as conn:
                response = await conn.query(query, {"target_id": target_id})

            items = []
            if response and isinstance(response, list):
                if len(response) > 0:
                    if isinstance(response[0], dict) and 'result' in response[0]:
                        items = response[0]['result']
                    else:
                        items = response

            logs = []
            for item in items:
                # Handle potential status wrapping if item is still wrapped (unlikely if items came from result)
                if 'status' in item and item['status'] != 'OK':
                    continue

                # Unwrap if needed (unlikely based on defensive logic above but to be safe)
                data = item

                # Parse timestamp
                ts_str = data.get('timestamp')
                timestamp = None
                if ts_str:
                    try:
                        timestamp = datetime.fromisoformat(ts_str.replace('Z', '+00:00'))
                    except ValueError:
                        pass

                # Handle ID
                log_id = str(data.get('id', ''))
                if log_id.startswith('audit_log:'):
                    log_id = log_id.split(':', 1)[1]

                logs.append(AuditLog(
                    id=log_id,
                    user_id=data.get('user_id'),
                    action=data.get('action'),
                    target_id=data.get('target_id'),
                    target_type=data.get('target_type'),
                    details=data.get('details', {}),
                    timestamp=timestamp
                ))
            return logs

        except Exception as e:
            logger.error(f"Failed to retrieve audit logs: {e}")
            return []
