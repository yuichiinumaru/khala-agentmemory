
import unittest
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.surprise_service import SurpriseService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector

class TestSurpriseService(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_gemini = AsyncMock()
        self.service = SurpriseService(gemini_client=self.mock_gemini)

    async def test_calculate_surprise_high(self):
        # Mock Gemini response for high surprise
        self.mock_gemini.generate_text.return_value = {
            "content": '{"surprise_score": 0.9, "reason": "Contradicts existing belief."}'
        }

        memory = Memory(
            user_id="user1",
            content="The sky is green.",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5)
        )

        context = [
            Memory(
                user_id="user1",
                content="The sky is blue.",
                tier=MemoryTier.LONG_TERM,
                importance=ImportanceScore(0.9)
            )
        ]

        score, reason = await self.service.calculate_surprise(memory, context)
        self.assertEqual(score, 0.9)
        self.assertEqual(reason, "Contradicts existing belief.")

    async def test_calculate_surprise_low(self):
        # Mock Gemini response for low surprise
        self.mock_gemini.generate_text.return_value = {
            "content": '{"surprise_score": 0.1, "reason": "Consistent with existing belief."}'
        }

        memory = Memory(
            user_id="user1",
            content="The sky is blue.",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5)
        )

        context = [
            Memory(
                user_id="user1",
                content="The sky is blue.",
                tier=MemoryTier.LONG_TERM,
                importance=ImportanceScore(0.9)
            )
        ]

        score, reason = await self.service.calculate_surprise(memory, context)
        self.assertEqual(score, 0.1)

    async def test_apply_surprise_boost(self):
        memory = Memory(
            user_id="user1",
            content="Surprise!",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5)
        )

        self.service.apply_surprise_boost(memory, 0.8, "Shocking")
        self.assertEqual(memory.metadata["surprise_score"], 0.8)
        self.assertEqual(memory.metadata["surprise_reason"], "Shocking")
