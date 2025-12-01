"""Audit repository implementation."""
import logging
from typing import Dict, Any, List, Optional
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
            timestamp: $timestamp,
            agent_id: $agent_id,
            operation: $operation,
            reason: $reason,
            before_state: $before_state,
            after_state: $after_state,
            memory_id: $memory_id
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

    async def get_agent_timeline(
        self,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[AuditLog]:
        """Retrieve timeline of agent activities."""
        where_clauses = ["agent_id = $agent_id"]
        params = {"agent_id": agent_id, "limit": limit}

        if start_time:
            where_clauses.append("timestamp >= $start_time")
            params["start_time"] = start_time.isoformat()

        if end_time:
            where_clauses.append("timestamp <= $end_time")
            params["end_time"] = end_time.isoformat()

        where_str = " AND ".join(where_clauses)

        query = f"""
        SELECT * FROM audit_log
        WHERE {where_str}
        ORDER BY timestamp DESC
        LIMIT $limit;
        """

        try:
            async with self.client.get_connection() as conn:
                result = await conn.query(query, params)

                rows = []
                if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
                    rows = result[0]['result']

                logs = []
                for row in rows:
                    ts_str = row['timestamp']
                    if ts_str.endswith('Z'):
                        ts_str = ts_str[:-1] + '+00:00'

                    # Handle action/operation mapping logic
                    # In DB: action might be object (details), operation is string
                    # In Entity: action is string
                    action_str = row.get('operation')
                    if not action_str:
                         # Fallback: if 'action' in DB is string, use it. If object, use empty or repr?
                         act = row.get('action')
                         if isinstance(act, str):
                             action_str = act
                         else:
                             action_str = "unknown"

                    logs.append(AuditLog(
                        id=row['id'],
                        user_id=row['user_id'],
                        action=action_str,
                        target_id=row['target_id'],
                        target_type=row['target_type'],
                        details=row.get('details') or {},
                        timestamp=datetime.fromisoformat(ts_str),
                        agent_id=row.get('agent_id'),
                        operation=row.get('operation'),
                        reason=row.get('reason'),
                        before_state=row.get('before_state'),
                        after_state=row.get('after_state')
                    ))
                return logs
        except Exception as e:
            logger.error(f"Failed to get agent timeline: {e}")
            return []
