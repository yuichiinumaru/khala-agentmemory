"""Service for analyzing agent activity timelines."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone

from khala.infrastructure.persistence.audit_repository import AuditRepository

logger = logging.getLogger(__name__)

class ActivityAnalysisService:
    """
    Strategy 104: Agent Activity Timeline.
    Provides methods to query and analyze agent activities from the audit log.
    """

    def __init__(self, audit_repository: AuditRepository):
        self.repository = audit_repository

    async def get_agent_timeline(
        self,
        agent_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Get a timeline of activities for a specific agent.
        """
        client = getattr(self.repository, 'client', None)
        if not client:
            return []

        query = """
        SELECT * FROM audit_log
        WHERE agent_id = $agent_id
        """
        params = {"agent_id": agent_id, "limit": limit}

        if start_time:
            query += " AND timestamp >= $start_time"
            params["start_time"] = start_time

        if end_time:
            query += " AND timestamp <= $end_time"
            params["end_time"] = end_time

        query += " ORDER BY timestamp DESC LIMIT $limit;"

        try:
            async with client.get_connection() as conn:
                response = await conn.query(query, params)
                if response and isinstance(response, list):
                     if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                         return response[0]['result']
                     return response
                return []
        except Exception as e:
            logger.error(f"Failed to fetch agent timeline: {e}")
            return []

    async def summarize_activity(self, agent_id: str, duration_hours: int = 24) -> Dict[str, Any]:
        """
        Summarize agent activity over the last N hours.
        """
        client = getattr(self.repository, 'client', None)
        if not client:
            return {}

        # Strategy 104: Activity Statistics
        query = """
        SELECT
            count() as total_actions,
            math::mean(timestamp - time::round(timestamp, 1h)) as activity_density,
            array::distinct(operation) as operations_performed
        FROM audit_log
        WHERE agent_id = $agent_id
        AND timestamp > time::now() - $duration;
        """

        # Duration string for SurrealDB (e.g., "24h")
        params = {
            "agent_id": agent_id,
            "duration": f"{duration_hours}h"
        }

        try:
             async with client.get_connection() as conn:
                response = await conn.query(query, params)
                if response and isinstance(response, list):
                     if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                         results = response[0]['result']
                         return results[0] if results else {}
                     return response[0] if response else {}
                return {}
        except Exception as e:
            logger.error(f"Failed to summarize activity: {e}")
            return {}
