"""
Graph Cache Service (Strategy 122: Path Lookup Acceleration).

Provides caching for expensive graph pathfinding operations.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone, timedelta

from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class GraphCacheService:
    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def cache_path(
        self,
        start_node: str,
        end_node: str,
        path: List[Dict[str, Any]],
        ttl_minutes: int = 60
    ) -> None:
        """Cache a graph path."""
        cache_id = self._generate_cache_key(start_node, end_node)

        expires_at = datetime.now(timezone.utc) + timedelta(minutes=ttl_minutes)

        existing = await self.db_client.get_cache_entry(cache_id)
        if existing:
             await self.db_client.update_cache_entry(cache_id, {
                 "value": {"path": path},
                 "expires_at": expires_at.isoformat(),
                 "created_at": datetime.now(timezone.utc).isoformat()
             })
        else:
             await self.db_client.create_cache_entry(
                 id=cache_id,
                 value={"path": path},
                 created_at=datetime.now(timezone.utc),
                 expires_at=expires_at,
                 access_count=0,
                 metadata={"type": "graph_path", "start": start_node, "end": end_node}
             )

    async def get_cached_path(self, start_node: str, end_node: str) -> Optional[List[Dict[str, Any]]]:
        """Retrieve a cached path if valid."""
        cache_id = self._generate_cache_key(start_node, end_node)

        entry = await self.db_client.get_cache_entry(cache_id)
        if not entry:
            return None

        # Check expiration
        expires_at = entry.get("expires_at")
        if expires_at:
            if isinstance(expires_at, str):
                if expires_at.endswith('Z'):
                    expires_at = expires_at[:-1]
                expires_at = datetime.fromisoformat(expires_at).replace(tzinfo=timezone.utc)

            if datetime.now(timezone.utc) > expires_at:
                # Expired
                return None

        # Update access count
        await self.db_client.update_cache_entry(cache_id, {
            "access_count": entry.get("access_count", 0) + 1
        })

        return entry.get("value", {}).get("path")

    def _generate_cache_key(self, start: str, end: str) -> str:
        return f"graph_path:{start}:{end}"
