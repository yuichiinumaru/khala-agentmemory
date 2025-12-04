"""Service for managing transient scratchpad memories (Strategy 149).

Scratchpads are temporary storage for complex reasoning, isolated by scope/project,
and designed to be ephemeral (short TTL).
"""

from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone, timedelta

from khala.domain.memory.entities import Memory
from khala.domain.memory.value_objects import MemoryTier, ImportanceScore
from khala.infrastructure.persistence.surrealdb_repository import SurrealDBMemoryRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class ScratchpadService:
    """Service for managing transient scratchpad memories."""

    def __init__(self, repository: SurrealDBMemoryRepository):
        self.repository = repository

    async def create_scratchpad(
        self,
        user_id: str,
        content: str,
        scope: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Memory:
        """Create a new scratchpad memory.

        Args:
            user_id: User/Agent ID
            content: Content of the scratchpad
            scope: Optional project/task scope (Strategy 148)
            metadata: Optional additional metadata

        Returns:
            The created Memory object
        """
        memory = Memory(
            user_id=user_id,
            content=content,
            tier=MemoryTier.SCRATCHPAD,
            importance=ImportanceScore.low(), # Default low importance for transient
            scope=scope,
            metadata=metadata or {},
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            accessed_at=datetime.now(timezone.utc)
        )

        await self.repository.create(memory)
        return memory

    async def get_scratchpad_content(
        self,
        user_id: str,
        scope: Optional[str] = None
    ) -> List[Memory]:
        """Retrieve active scratchpad memories for a user/scope."""
        # Using search_memories_by_bm25 with empty query to filter by metadata if repo supported it,
        # but repo.get_by_tier is better here.
        # We need to filter by scope manually if get_by_tier doesn't support it yet.

        # Actually, get_by_tier does NOT support scope filtering in current implementation.
        # But we can use search_by_text with filters.

        filters = {"tier": MemoryTier.SCRATCHPAD.value}
        if scope:
            filters["scope"] = scope

        # Empty query text to match all (BM25 might require strict match,
        # so relying on filters solely with empty query might not work if @@ requires token).
        # Alternatively, we can use client directly for a custom query or extend repository.
        # Let's use get_by_tier and filter in memory for now, or use client.

        # Better approach: Add get_by_tier_and_scope to repository?
        # Or just use client query.

        query = """
        SELECT * FROM memory
        WHERE user_id = $user_id
        AND tier = $tier
        AND is_archived = false
        """
        params = {
            "user_id": user_id,
            "tier": MemoryTier.SCRATCHPAD.value
        }

        if scope:
            query += " AND scope = $scope"
            params["scope"] = scope

        query += " ORDER BY created_at DESC;"

        async with self.repository.client.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                # Handle nested response
                data = response
                if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                    data = response[0]['result']

                return [self.repository.client._deserialize_memory(m) for m in data]

        return []

    async def clear_scratchpad(
        self,
        user_id: str,
        scope: Optional[str] = None
    ) -> None:
        """Clear (archive/delete) scratchpad memories."""
        memories = await self.get_scratchpad_content(user_id, scope)
        for memory in memories:
            # We can delete them directly since they are transient
            await self.repository.delete(memory.id)

    async def cleanup_expired(self) -> int:
        """Background job to cleanup expired scratchpads (older than TTL)."""
        # TTL is 1 hour for SCRATCHPAD
        cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

        query = """
        DELETE memory
        WHERE tier = 'scratchpad'
        AND created_at < $cutoff;
        """

        params = {"cutoff": cutoff.isoformat()}

        async with self.repository.client.get_connection() as conn:
            # SurrealDB DELETE returns deleted records? or nothing.
            # We assume it works.
            await conn.query(query, params)

        return 0 # Cannot easily get count of deleted items without extra query
