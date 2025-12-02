import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.repository import MemoryRepository
from khala.application.services.memory_lifecycle import MemoryLifecycleService
from khala.domain.memory.services import MemoryService, DecayService, DeduplicationService, ConsolidationService

class TestMemoryLifecycleService(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.repository = MagicMock(spec=MemoryRepository)
        # Mock async methods of the repository
        self.repository.get_by_tier = AsyncMock(return_value=[])
        self.repository.find_duplicate_groups = AsyncMock(return_value=[])
        self.repository.update = AsyncMock()
        self.repository.create = AsyncMock()
        self.repository.delete = AsyncMock()
        self.repository.client = MagicMock()

        self.memory_service = MagicMock(spec=MemoryService)
        self.decay_service = MagicMock(spec=DecayService)
        self.deduplication_service = MagicMock(spec=DeduplicationService)
        self.consolidation_service = MagicMock(spec=ConsolidationService)

        self.gemini_client = MagicMock()
        self.service = MemoryLifecycleService(
            repository=self.repository,
            gemini_client=self.gemini_client,
            memory_service=self.memory_service,
            decay_service=self.decay_service,
            deduplication_service=self.deduplication_service,
            consolidation_service=self.consolidation_service
        )

    async def test_promote_memories(self):
        # Create a memory that is ready for promotion
        memory = Memory(
            user_id="u1", content="promotable", tier=MemoryTier.WORKING, importance=ImportanceScore(0.9),
            created_at=datetime.now(timezone.utc) - timedelta(hours=1),
            access_count=10
        )

        # Mock repo to return this memory for WORKING tier
        self.repository.get_by_tier.side_effect = lambda uid, tier, limit: [memory] if tier == "working" else []

        count = await self.service.promote_memories("u1")

        self.assertEqual(count, 1)
        self.assertEqual(memory.tier, MemoryTier.SHORT_TERM)
        self.repository.update.assert_called_with(memory)

    async def test_decay_and_archive_memories(self):
        memory = Memory(
            user_id="u1", content="decayable", tier=MemoryTier.WORKING, importance=ImportanceScore(0.1),
            access_count=0,
            created_at=datetime.now(timezone.utc) - timedelta(days=100)
        )

        # Mock repo
        self.repository.get_by_tier.side_effect = lambda uid, tier, limit: [memory] if tier == "working" else []

        # Mock decay service to actually mark it as archival candidate
        self.decay_service.should_archive_based_on_decay.return_value = True

        stats = await self.service.decay_and_archive_memories("u1")

        self.assertEqual(stats["decayed"], 1)
        self.assertEqual(stats["archived"], 1)
        self.assertTrue(memory.is_archived)
        self.repository.update.assert_called()

    async def test_deduplicate_memories_exact(self):
        m1 = Memory(id="1", user_id="u1", content="same", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5))
        m2 = Memory(id="2", user_id="u1", content="same", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5))

        # Mock find_duplicate_groups to return m1 and m2 as a group
        self.repository.find_duplicate_groups.return_value = [[m1, m2]]

        # Mock get_by_tier for semantic search part (empty to avoid interference)
        self.repository.get_by_tier.return_value = []

        count = await self.service.deduplicate_memories("u1")

        self.assertEqual(count, 1)
        self.assertTrue(m2.is_archived)
        self.assertEqual(m2.metadata["duplicate_of"], "1")
        self.repository.update.assert_called_with(m2)

    async def test_run_lifecycle_job(self):
        # Just ensure it calls everything
        self.service.promote_memories = AsyncMock(return_value=1)
        self.service.decay_and_archive_memories = AsyncMock(return_value={"decayed": 2, "archived": 1})
        self.service.deduplicate_memories = AsyncMock(return_value=3)
        self.service.consolidate_memories = AsyncMock(return_value=0)

        stats = await self.service.run_lifecycle_job("u1")

        self.assertEqual(stats["promoted"], 1)
        self.assertEqual(stats["decayed"], 2)
        self.assertEqual(stats["archived"], 1)
        self.assertEqual(stats["deduplicated"], 3)

        self.service.promote_memories.assert_called_once()
        self.service.decay_and_archive_memories.assert_called_once()
        self.service.deduplicate_memories.assert_called_once()
