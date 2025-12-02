import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.hybrid_search_service import HybridSearchService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector

class TestHybridSearchWeights(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_repo = AsyncMock()
        self.mock_embedding_service = AsyncMock()
        self.mock_embedding_service.get_embedding.return_value = [0.1] * 768

        self.service = HybridSearchService(
            memory_repository=self.mock_repo,
            embedding_service=self.mock_embedding_service
        )

    async def test_weighting_influence(self):
        # Create two memories
        # Note: Tier and Importance need enum/class or string if constructor handles it.
        # Entity code expects Enum or compatible string if post_init converts it?
        # Actually dataclass expects the type.

        mem_vec = Memory(
            user_id="u1",
            content="Vector Winner",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5),
            id="m1"
        )
        mem_text = Memory(
            user_id="u1",
            content="Text Winner",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5),
            id="m2"
        )

        # Scenario:
        # m1 is rank 1 in Vector, not in Text
        # m2 is rank 1 in Text, not in Vector

        self.mock_repo.search_by_vector.return_value = [mem_vec]
        self.mock_repo.search_by_text.return_value = [mem_text]

        # Test 1: Vector favored (weight 10 vs 1)
        results_vec = await self.service.search(
            query="q", user_id="u1", vector_weight=10.0, bm25_weight=1.0, top_k=2
        )
        # m1 should be first
        self.assertEqual(results_vec[0].id, "m1")
        self.assertEqual(results_vec[1].id, "m2")

        # Test 2: Text favored (weight 1 vs 10)
        results_text = await self.service.search(
            query="q", user_id="u1", vector_weight=1.0, bm25_weight=10.0, top_k=2
        )
        self.assertEqual(results_text[0].id, "m2")
        self.assertEqual(results_text[1].id, "m1")

if __name__ == "__main__":
    unittest.main()
