"""
Migration Path Tracking Service (Strategy 114).

Tracks how an idea (concept) moves between agents/regions.
"""

from typing import List, Dict, Any, Optional
import logging
from khala.infrastructure.persistence.audit_repository import AuditRepository
from khala.domain.audit.entities import AuditLog

logger = logging.getLogger(__name__)

class MigrationTrackingService:
    """Service for tracking the migration path of a memory."""

    def __init__(self, audit_repository: AuditRepository):
        self.audit_repository = audit_repository

    async def track_memory_path(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        Trace the migration path of a memory across agents.

        Args:
            memory_id: The ID of the memory to track.

        Returns:
            List of steps describing the path.
            Each step: {
                "step": int,
                "agent_id": str,
                "action": str,
                "timestamp": str (ISO),
                "details": dict
            }
        """
        logs = await self.audit_repository.get_logs_by_target(memory_id)

        if not logs:
            return []

        path = []
        step_count = 1

        # Logs are already sorted by the repository
        for log in logs:
            # We are interested in interactions by agents (user_id).
            # We treat every interaction as a "visit" or "move" to that agent's context.

            # Skip system actions if needed, but for now include all.

            step = {
                "step": step_count,
                "agent_id": log.user_id,
                "action": log.action,
                "timestamp": log.timestamp.isoformat() if log.timestamp else None,
                "details": log.details
            }
            path.append(step)
            step_count += 1

        return path
