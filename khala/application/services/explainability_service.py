"""Explainability Service (Strategy 76).

This service is responsible for storing and retrieving reasoning traces and explainability graphs.
It supports:
1. Storing reasoning paths (Strategy 76).
2. Storing Dr. MAMR reasoning traces (Strategy 168/169).
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class ExplainabilityService:
    """Service for managing explainability graphs and reasoning traces."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def store_reasoning_path(
        self,
        query_entity: str,
        target_entity: str,
        path: List[Dict[str, Any]],
        llm_explanation: str,
        confidence: float,
        final_rank: int
    ) -> str:
        """
        Store a reasoning path (graph traversal explanation).

        Args:
            query_entity: ID of the starting entity/concept.
            target_entity: ID of the result entity/concept.
            path: List of nodes/edges traversed.
            llm_explanation: Natural language explanation of the path.
            confidence: Confidence score of this reasoning chain.
            final_rank: Rank of this result in the search.

        Returns:
            ID of the created record.
        """
        query = """
        CREATE reasoning_paths CONTENT {
            query_entity: $query_entity,
            target_entity: $target_entity,
            path: $path,
            llm_explanation: $llm_explanation,
            confidence: $confidence,
            final_rank: $final_rank,
            created_at: time::now()
        };
        """

        params = {
            "query_entity": query_entity,
            "target_entity": target_entity,
            "path": path,
            "llm_explanation": llm_explanation,
            "confidence": confidence,
            "final_rank": final_rank
        }

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query, params)

                if isinstance(response, list) and len(response) > 0:
                    item = response[0]
                    if isinstance(item, dict):
                         if 'id' in item:
                             return item['id']
                         if 'result' in item and isinstance(item['result'], list) and len(item['result']) > 0:
                             return item['result'][0]['id']
                return ""
        except Exception as e:
            logger.error(f"Failed to store reasoning path: {e}")
            raise

    async def get_reasoning_paths(
        self,
        query_entity: Optional[str] = None,
        target_entity: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Retrieve reasoning paths filtering by query or target entity."""

        where_clauses = []
        params = {"limit": limit}

        if query_entity:
            where_clauses.append("query_entity = $query_entity")
            params["query_entity"] = query_entity

        if target_entity:
            where_clauses.append("target_entity = $target_entity")
            params["target_entity"] = target_entity

        where_str = ""
        if where_clauses:
            where_str = "WHERE " + " AND ".join(where_clauses)

        query = f"""
        SELECT * FROM reasoning_paths
        {where_str}
        ORDER BY created_at DESC
        LIMIT $limit;
        """

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query, params)
                if response and isinstance(response, list):
                     if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                         return response[0]['result']
                     return response
                return []
        except Exception as e:
            logger.error(f"Failed to get reasoning paths: {e}")
            return []

    async def store_mamr_trace(
        self,
        meta_decision: str,
        reasoning_step: str,
        group_advantage: float
    ) -> str:
        """
        Store a Dr. MAMR reasoning trace (Strategy 168).

        Args:
            meta_decision: The high-level decision/strategy chosen.
            reasoning_step: The actual reasoning content/step executed.
            group_advantage: Score indicating advantage of this group/strategy.

        Returns:
            ID of the created record.
        """
        query = """
        CREATE reasoning_traces CONTENT {
            meta_decision: $meta_decision,
            reasoning_step: $reasoning_step,
            group_advantage: $group_advantage,
            created_at: time::now()
        };
        """

        params = {
            "meta_decision": meta_decision,
            "reasoning_step": reasoning_step,
            "group_advantage": group_advantage
        }

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query, params)
                if isinstance(response, list) and len(response) > 0:
                    item = response[0]
                    if isinstance(item, dict):
                         if 'id' in item:
                             return item['id']
                         if 'result' in item and isinstance(item['result'], list) and len(item['result']) > 0:
                             return item['result'][0]['id']
                return ""
        except Exception as e:
            logger.error(f"Failed to store MAMR trace: {e}")
            raise

    async def get_recent_traces(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent reasoning traces for analysis."""
        query = """
        SELECT * FROM reasoning_traces
        ORDER BY created_at DESC
        LIMIT $limit;
        """

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query, {"limit": limit})
                if response and isinstance(response, list):
                     if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                         return response[0]['result']
                     return response
                return []
        except Exception as e:
            logger.error(f"Failed to get reasoning traces: {e}")
            return []
