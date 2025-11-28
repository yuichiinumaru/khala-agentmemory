import pytest
from unittest.mock import MagicMock, AsyncMock
from typing import List

from khala.application.services.hybrid_search_service import HybridSearchService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore, EmbeddingVector
from khala.domain.memory.repository import MemoryRepository
from khala.domain.ports.embedding_service import EmbeddingService
from datetime import datetime

# Mock implementations
class MockEmbeddingService(EmbeddingService):
    async def get_embedding(self, text: str) -> List[float]:
        return [0.1] * 768

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        return [[0.1] * 768 for _ in texts]

class MockMemoryRepository(MemoryRepository):
    def __init__(self):
        self.memories = {}

    async def create(self, memory: Memory) -> str:
        self.memories[memory.id] = memory
        return memory.id

    async def get_by_id(self, memory_id: str):
        return self.memories.get(memory_id)

    async def update(self, memory: Memory) -> None:
        self.memories[memory.id] = memory

    async def delete(self, memory_id: str) -> None:
        if memory_id in self.memories:
            del self.memories[memory_id]

    async def search_by_vector(self, embedding, user_id, top_k=10, min_similarity=0.6, filters=None):
        # Return dummy results: mem-1, mem-0, mem-2
        mems = list(self.memories.values())
        # Assuming created in order 0, 1, 2. mems[1] is mem-1
        return [mems[1], mems[0], mems[2]][:top_k]

    async def search_by_text(self, query_text, user_id, top_k=10, filters=None):
         # Return dummy results: mem-1, mem-2, mem-0
        mems = list(self.memories.values())
        return [mems[1], mems[2], mems[0]][:top_k]

    async def get_by_tier(self, user_id, tier, limit=100):
        return []

@pytest.mark.asyncio
async def test_hybrid_search_logic():
    # Setup
    repo = MockMemoryRepository()
    embedding_service = MockEmbeddingService()
    service = HybridSearchService(repo, embedding_service)

    # Create dummy memories
    for i in range(3):
        m = Memory(
            id=f"mem-{i}",
            user_id="user-1",
            content=f"Test memory {i}",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium(),
            embedding=EmbeddingVector([0.1]*768),
            created_at=datetime.now(),
            updated_at=datetime.now(),
            accessed_at=datetime.now()
        )
        await repo.create(m)

    # Execute Search
    results = await service.search("test", "user-1", top_k=2)

    # Verify
    assert len(results) == 2
    # Verify that we got Memory objects
    assert isinstance(results[0], Memory)

    # Since vector search returns [0, 1, 2] and text search returns [2, 1, 0]
    # RRF should balance them.
    # mem-0: vector rank 0 (score 1/61), text rank 2 (score 1/63)
    # mem-1: vector rank 1 (score 1/62), text rank 1 (score 1/62) -> highest score 2/62 = 1/31 ~ 0.0322
    # mem-2: vector rank 2 (score 1/63), text rank 0 (score 1/61)

    # mem-1 should be first
    assert results[0].id == "mem-1"
