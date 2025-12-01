import unittest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

from khala.domain.memory.services.conflict_resolution import ConflictResolutionService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector

class TestConflictResolutionService(unittest.IsolatedAsyncioTestCase):

    async def asyncSetUp(self):
        self.mock_repo = MagicMock()
        self.mock_repo.search_by_vector = AsyncMock()
        self.service = ConflictResolutionService(self.mock_repo)

        self.vector = EmbeddingVector([0.1] * 768)
        self.memory = Memory(
            user_id="user1",
            content="The sky is blue.",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5),
            embedding=self.vector,
            id="mem1"
        )

    async def test_find_potential_conflicts_returns_candidates(self):
        # Create a candidate that is similar but different content
        candidate = Memory(
            user_id="user1",
            content="The sky is green.",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5),
            embedding=self.vector,
            id="mem2"
        )

        # Mock repo to return the candidate + the original memory
        self.mock_repo.search_by_vector.return_value = [self.memory, candidate]

        conflicts = await self.service.find_potential_conflicts(self.memory)

        self.assertEqual(len(conflicts), 1)
        self.assertEqual(conflicts[0].id, "mem2")
        self.assertEqual(conflicts[0].content, "The sky is green.")

    async def test_find_potential_conflicts_excludes_self(self):
        self.mock_repo.search_by_vector.return_value = [self.memory]

        conflicts = await self.service.find_potential_conflicts(self.memory)

        self.assertEqual(len(conflicts), 0)

    async def test_find_potential_conflicts_excludes_exact_content_duplicates(self):
        # Exact duplicate memory (different ID but same content)
        duplicate = Memory(
            user_id="user1",
            content="The sky is blue.",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5),
            embedding=self.vector,
            id="mem2"
        )

        self.mock_repo.search_by_vector.return_value = [duplicate]

        conflicts = await self.service.find_potential_conflicts(self.memory)

        self.assertEqual(len(conflicts), 0)

    async def test_no_embedding_returns_empty(self):
        memory_no_vec = Memory(
            user_id="user1",
            content="No vector",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5),
            embedding=None
        )

        conflicts = await self.service.find_potential_conflicts(memory_no_vec)
        self.assertEqual(len(conflicts), 0)

if __name__ == '__main__':
    unittest.main()
