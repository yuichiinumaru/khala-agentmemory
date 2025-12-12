import unittest
from unittest.mock import MagicMock, AsyncMock
import asyncio
from khala.application.services.self_challenging_service import SelfChallengingService
from khala.domain.memory.entities import Memory, MemoryTier, MemorySource
from khala.domain.memory.value_objects import ImportanceScore
from khala.infrastructure.gemini.client import GeminiClient

class TestSelfChallengingService(unittest.TestCase):
    def setUp(self):
        self.mock_gemini = MagicMock(spec=GeminiClient)
        self.service = SelfChallengingService(self.mock_gemini)

        # Create dummy memories
        self.mem1 = Memory(
            content="Paris is the capital of France.",
            tier=MemoryTier.LONG_TERM,
            source=MemorySource(source_type=MemorySource.USER_INPUT),
            importance=ImportanceScore.medium(),
            user_id="test_user"
        )
        self.mem2 = Memory(
            content="Paris is a city in Texas.",
            tier=MemoryTier.LONG_TERM,
            source=MemorySource(source_type=MemorySource.USER_INPUT),
            importance=ImportanceScore.medium(),
            user_id="test_user"
        )

    def test_challenge_memories(self):
        # Mock Gemini response
        mock_response = """
        [
            {
                "memory_index": 0,
                "status": "PASS",
                "reason": "Correctly answers the query about France.",
                "confidence": 0.95
            },
            {
                "memory_index": 1,
                "status": "FAIL",
                "reason": "Refers to Paris, Texas, not France.",
                "confidence": 0.9
            }
        ]
        """
        self.mock_gemini.generate_content = AsyncMock(return_value=mock_response)

        query = "What is the capital of France?"
        results = asyncio.run(self.service.challenge_memories(query, [self.mem1, self.mem2]))

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["status"], "PASS")
        self.assertEqual(results[1]["status"], "FAIL")

    def test_filter_memories(self):
         # Mock Gemini response
        mock_response = """
        [
            {
                "memory_index": 0,
                "status": "PASS",
                "reason": "Correct",
                "confidence": 0.95
            },
            {
                "memory_index": 1,
                "status": "FAIL",
                "reason": "Incorrect context",
                "confidence": 0.9
            }
        ]
        """
        self.mock_gemini.generate_content = AsyncMock(return_value=mock_response)

        query = "What is the capital of France?"
        filtered = asyncio.run(self.service.filter_memories(query, [self.mem1, self.mem2]))

        self.assertEqual(len(filtered), 1)
        self.assertEqual(filtered[0].content, "Paris is the capital of France.")

if __name__ == "__main__":
    unittest.main()
