from typing import List, Optional, Dict, Any
import logging
import hashlib

from khala.domain.memory.repository import MemoryRepository
from khala.domain.memory.entities import Memory
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
        """Save a new memory with transactional audit logging."""
        async with self.client.transaction() as conn:
            memory_id = await self.client.create_memory(memory, connection=conn)

            await self.audit_repo.log(AuditLog(
                user_id=memory.user_id,
                action="create",
                target_id=memory_id,
                target_type="memory",
                details={"tier": memory.tier.value}
            ), connection=conn)

            return memory_id
        
    async def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by its ID."""
        return await self.client.get_memory(memory_id)
        
    async def update(self, memory: Memory) -> None:
        """Update an existing memory with transactional audit logging."""
        async with self.client.transaction() as conn:
            await self.client.update_memory(memory, connection=conn)

            await self.audit_repo.log(AuditLog(
                user_id=memory.user_id,
                action="update",
                target_id=memory.id,
                target_type="memory",
                details={"tier": memory.tier.value}
            ), connection=conn)
        
    async def delete(self, memory_id: str) -> None:
        """Delete a memory with transactional audit logging."""
        # We need to fetch the memory first to get user_id for audit
        # This read happens outside the write transaction, which is acceptable
        # unless strict serializability is needed for the read.
        memory = await self.get_by_id(memory_id)
        user_id = memory.user_id if memory else "unknown"

        async with self.client.transaction() as conn:
            await self.client.delete_memory(memory_id, connection=conn)

            await self.audit_repo.log(AuditLog(
                user_id=user_id,
                action="delete",
                target_id=memory_id,
                target_type="memory",
                details={}
            ), connection=conn)
        
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

    async def find_duplicate_groups(self, user_id: str) -> List[List[Memory]]:
        """Find groups of duplicate memories (exact match)."""
        # 1. Find hashes with duplicates
        query = """
        SELECT content_hash, count() as count
        FROM memory
        WHERE user_id = $user_id
        AND is_archived = false
        GROUP BY content_hash
        HAVING count > 1;
        """

        async with self.client.get_connection() as conn:
            response = await conn.query(query, {"user_id": user_id})

            hashes = []
            if response and isinstance(response, list):
                # Handle SurrealDB response structure
                items = response
                if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']

                for item in items:
                    if isinstance(item, dict) and 'content_hash' in item:
                        hashes.append(item['content_hash'])

            if not hashes:
                return []

            # 2. Fetch memories for these hashes
            duplicate_groups = []

            # Batch query for hashes
            batch_size = 50
            for i in range(0, len(hashes), batch_size):
                batch_hashes = hashes[i:i+batch_size]
                batch_query = """
                SELECT * FROM memory
                WHERE user_id = $user_id
                AND is_archived = false
                AND content_hash IN $hashes
                ORDER BY created_at ASC;
                """

                resp = await conn.query(batch_query, {"user_id": user_id, "hashes": batch_hashes})

                memories = []
                if resp and isinstance(resp, list):
                     data = resp
                     if len(resp) > 0 and isinstance(resp[0], dict) and 'result' in resp[0]:
                         data = resp[0]['result']

                     memories = [self.client._deserialize_memory(m) for m in data]

                # Group by hash locally
                groups = {}
                for mem in memories:
                    # Re-calculate hash to group them
                    h = hashlib.sha256(f"{mem.content}{mem.user_id}".encode()).hexdigest()

                    if h not in groups:
                        groups[h] = []
                    groups[h].append(mem)

                duplicate_groups.extend(list(groups.values()))

            return duplicate_groups
