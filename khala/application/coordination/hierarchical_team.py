"""Hierarchical Team Coordination (Module 13.3.2 - FULORA)."""

import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class HierarchicalTeamService:
    """Manages high-level guidance and low-level action coordination."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def register_guidance(self, decision_id: str, action_id: str, guidance_type: str) -> None:
        """Record a guidance edge from high-level decision to low-level action."""
        query = """
        CREATE hierarchical_coordination CONTENT {
            from_decision: $from_decision,
            to_action: $to_action,
            guidance_type: $guidance_type,
            created_at: time::now()
        };
        """
        params = {
            "from_decision": decision_id,
            "to_action": action_id,
            "guidance_type": guidance_type
        }
        async with self.db_client.get_connection() as conn:
            await conn.query(query, params)

    async def get_guidance_history(self, action_id: str) -> List[Dict[str, Any]]:
        """Retrieve guidance that led to an action."""
        query = """
        SELECT * FROM hierarchical_coordination WHERE to_action = $action_id;
        """
        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, {"action_id": action_id})
            if response and isinstance(response, list) and response:
                items = response
                if isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']
                return items
        return []
