from typing import List, Optional, Dict, Any
import logging

from khala.domain.memory.repository import MemoryRepository
from khala.domain.memory.entities import Memory, Relationship
from khala.domain.memory.value_objects import EmbeddingVector
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.persistence.audit_repository import AuditRepository
from khala.domain.audit.entities import AuditLog

logger = logging.getLogger(__name__)

class SurrealDBMemoryRepository(MemoryRepository):
    """
    SurrealDB implementation of the MemoryRepository interface with Audit Logging.
    """
    
    def __init__(self, client: SurrealDBClient, audit_repo: Optional[AuditRepository] = None):
        self.client = client
        self.audit_repo = audit_repo or AuditRepository(client)
        
    async def create(self, memory: Memory) -> str:
        """Save a new memory."""
        memory_id = await self.client.create_memory(memory)
        await self.audit_repo.log(AuditLog(
            user_id=memory.user_id,
            action="create",
            target_id=memory_id,
            target_type="memory",
            details={"tier": memory.tier.value}
        ))
        return memory_id
        
    async def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by its ID."""
        # Auditing reads might be too verbose, but can be enabled if strict audit is required.
        # For now, we only audit state changes.
        return await self.client.get_memory(memory_id)
        
    async def update(self, memory: Memory) -> None:
        """Update an existing memory."""
        await self.client.update_memory(memory)
        await self.audit_repo.log(AuditLog(
            user_id=memory.user_id,
            action="update",
            target_id=memory.id,
            target_type="memory",
            details={"tier": memory.tier.value}
        ))
        
    async def delete(self, memory_id: str) -> None:
        """Delete a memory."""
        # We need to fetch the memory first to get user_id for audit
        memory = await self.get_by_id(memory_id)
        user_id = memory.user_id if memory else "unknown"

        await self.client.delete_memory(memory_id)
        await self.audit_repo.log(AuditLog(
            user_id=user_id,
            action="delete",
            target_id=memory_id,
            target_type="memory",
            details={}
        ))
        
    async def search_by_vector(
        self, 
        embedding: EmbeddingVector, 
        user_id: str, 
        top_k: int = 10, 
        min_similarity: float = 0.6,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Memory]:
        """Search memories by vector similarity."""
        results = await self.client.search_memories_by_vector(
            embedding=embedding,
            user_id=user_id,
            top_k=top_k,
            min_similarity=min_similarity,
            filters=filters
        )
        return [self.client._deserialize_memory(data) for data in results]
        
    async def search_by_text(
        self, 
        query_text: str, 
        user_id: str, 
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Memory]:
        """Search memories by text (BM25/Full-text)."""
        results = await self.client.search_memories_by_bm25(
            query_text=query_text,
            user_id=user_id,
            top_k=top_k,
            filters=filters
        )
        return [self.client._deserialize_memory(data) for data in results]
        
    async def get_by_tier(
        self, 
        user_id: str, 
        tier: str, 
        limit: int = 100
    ) -> List[Memory]:
        """Retrieve memories by tier."""
        return await self.client.get_memories_by_tier(
            user_id=user_id,
            tier=tier,
            limit=limit
        )

    async def get_relationships(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 1000
    ) -> List[Relationship]:
        """Retrieve relationships based on filters."""
        results = await self.client.get_relationships(filters=filters, limit=limit)
        return [self._deserialize_relationship(data) for data in results]

    def _deserialize_relationship(self, data: Dict[str, Any]) -> Relationship:
        """Helper to deserialize relationship data."""
        from datetime import datetime, timezone

        def parse_dt(dt_val: Any) -> Optional[datetime]:
            if not dt_val: return None
            if isinstance(dt_val, str):
                if dt_val.endswith('Z'): dt_val = dt_val[:-1]
                return datetime.fromisoformat(dt_val).replace(tzinfo=timezone.utc)
            return dt_val

        rel_id = str(data["id"])
        if rel_id.startswith("relationship:"):
            rel_id = rel_id.split(":", 1)[1]

        return Relationship(
            id=rel_id,
            from_entity_id=data["from_entity_id"],
            to_entity_id=data["to_entity_id"],
            relation_type=data["relation_type"],
            strength=data.get("strength", 0.0),
            valid_from=parse_dt(data.get("valid_from")) or datetime.now(timezone.utc),
            valid_to=parse_dt(data.get("valid_to")),
            transaction_time_start=parse_dt(data.get("transaction_time_start")) or datetime.now(timezone.utc),
            transaction_time_end=parse_dt(data.get("transaction_time_end"))
        )
