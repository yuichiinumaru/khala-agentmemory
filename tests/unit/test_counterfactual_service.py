
import unittest
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.counterfactual_service import CounterfactualService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

class TestCounterfactualService(unittest.IsolatedAsyncioTestCase):

    def setUp(self):
        self.mock_repo = AsyncMock()
        self.mock_gemini = AsyncMock()
        self.service = CounterfactualService(repository=self.mock_repo, gemini_client=self.mock_gemini)

    async def test_generate_counterfactuals(self):
        original_memory = Memory(
            id="mem1",
            user_id="user1",
            content="I walked to the store.",
            tier=MemoryTier.LONG_TERM,
            importance=ImportanceScore(0.5)
        )
        self.mock_repo.get_by_id.return_value = original_memory

        self.mock_gemini.generate_text.return_value = {
            "content": "If you had driven, you would have arrived sooner."
        }

        results = await self.service.generate_counterfactuals(
            memory_id="mem1",
            what_if_prompt="What if I drove?"
        )

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0].content, "If you had driven, you would have arrived sooner.")
        self.assertEqual(results[0].metadata["type"], "counterfactual")
        self.assertEqual(results[0].metadata["original_memory_id"], "mem1")
        self.assertEqual(results[0].metadata["hypothesis"], "What if I drove?")

    async def test_save_simulation(self):
        memories = [
            Memory(user_id="u1", content="sim1", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5))
        ]
        self.mock_repo.create.return_value = "mem_id_1"

        ids = await self.service.save_simulation(memories)

        self.assertEqual(ids, ["mem_id_1"])
        self.mock_repo.create.assert_called_once()
