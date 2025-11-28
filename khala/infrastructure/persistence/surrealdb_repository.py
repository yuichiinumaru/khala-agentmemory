from typing import List, Optional, Dict, Any
import logging

from khala.domain.memory.repository import MemoryRepository
from khala.domain.memory.entities import Memory
from khala.domain.memory.value_objects import EmbeddingVector
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class SurrealDBMemoryRepository(MemoryRepository):
    """
    SurrealDB implementation of the MemoryRepository interface.
    """
    
    def __init__(self, client: SurrealDBClient):
        self.client = client
        
    async def create(self, memory: Memory) -> str:
        """Save a new memory."""
        return await self.client.create_memory(memory)
        
    async def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by its ID."""
        return await self.client.get_memory(memory_id)
        
    async def update(self, memory: Memory) -> None:
        """Update an existing memory."""
        await self.client.update_memory(memory)
        
    async def delete(self, memory_id: str) -> None:
        """Delete a memory."""
        await self.client.delete_memory(memory_id)
        
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
        # Convert dict results to Memory objects
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
