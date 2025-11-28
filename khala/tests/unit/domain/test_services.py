import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock

from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector, DecayScore
from khala.domain.memory.services import (
    MemoryService,
    DecayService,
    DeduplicationService,
    ConsolidationService
)

class TestMemoryService(unittest.TestCase):
    def setUp(self):
        self.service = MemoryService()

    def test_calculate_promotion_score(self):
        memory = Memory(
            user_id="user1",
            content="test",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.8)
        )
        # Manually set age to > 0.5 hours
        memory.created_at = datetime.now(timezone.utc) - timedelta(hours=1)

        score = self.service.calculate_promotion_score(memory)
        self.assertGreater(score, 0.0)

    def test_should_consolidate(self):
        memories = []
        for _ in range(101):
            memories.append(Memory(
                user_id="user1",
                content="test",
                tier=MemoryTier.WORKING,
                importance=ImportanceScore(0.5)
            ))

        self.assertTrue(self.service.should_consolidate(memories))
        self.assertFalse(self.service.should_consolidate(memories[:50]))


class TestDecayService(unittest.TestCase):
    def setUp(self):
        self.service = DecayService()

    def test_update_decay_score(self):
        memory = Memory(
            user_id="user1",
            content="test",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(1.0)
        )
        # Create memory 30 days old (1 half-life)
        memory.created_at = datetime.now(timezone.utc) - timedelta(days=30)

        self.service.update_decay_score(memory)

        self.assertIsNotNone(memory.decay_score)
        # Expected decay: 1.0 * exp(-30/30) = 1.0 * 0.367...
        self.assertAlmostEqual(memory.decay_score.value, 0.367879, places=2)

    def test_should_archive_based_on_decay(self):
        memory = Memory(
            user_id="user1",
            content="test",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.1) # Very low importance
        )
        # Very old
        memory.created_at = datetime.now(timezone.utc) - timedelta(days=365)
        memory.access_count = 0

        # Should trigger low decay score
        self.service.update_decay_score(memory)

        self.assertTrue(self.service.should_archive_based_on_decay(memory))


class TestDeduplicationService(unittest.TestCase):
    def setUp(self):
        self.service = DeduplicationService()

    def test_find_exact_duplicates(self):
        m1 = Memory(user_id="u1", content="hello world", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5))
        m2 = Memory(user_id="u1", content="hello world", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5))
        m3 = Memory(user_id="u1", content="different", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5))

        duplicates = self.service.find_exact_duplicates(m1, [m2, m3])
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0].id, m2.id)

    def test_find_semantic_duplicates(self):
        # [1, 0] vs [1, 0] -> sim 1.0
        # [1, 0] vs [0, 1] -> sim 0.0

        m1 = Memory(
            user_id="u1", content="a", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5),
            embedding=EmbeddingVector([1.0] + [0.0]*767)
        )
        m2 = Memory(
            user_id="u1", content="b", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5),
            embedding=EmbeddingVector([0.99] + [0.0]*767) # Very similar
        )
        m3 = Memory(
            user_id="u1", content="c", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5),
            embedding=EmbeddingVector([0.0] + [1.0]*767) # Orthogonal
        )

        duplicates = self.service.find_semantic_duplicates(m1, [m2, m3], threshold=0.9)
        self.assertEqual(len(duplicates), 1)
        self.assertEqual(duplicates[0].id, m2.id)


class TestConsolidationService(unittest.TestCase):
    def setUp(self):
        self.service = ConsolidationService()

    def test_group_memories(self):
        m1 = Memory(user_id="u1", content="a", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5), category="cat1")
        m2 = Memory(user_id="u1", content="b", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5), category="cat1")
        m3 = Memory(user_id="u1", content="c", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5), category="cat2")
        m4 = Memory(user_id="u1", content="d", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5)) # No category

        groups = self.service.group_memories_for_consolidation([m1, m2, m3, m4])

        # We expect 3 groups: [m1, m2], [m3], [m4]
        self.assertEqual(len(groups), 3)

        # Verify group sizes (order might vary depending on dict implementation, but values length shouldn't)
        sizes = sorted([len(g) for g in groups])
        self.assertEqual(sizes, [1, 1, 2])
