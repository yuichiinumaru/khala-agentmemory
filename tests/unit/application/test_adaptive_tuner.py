import unittest
from unittest.mock import MagicMock, AsyncMock
import asyncio
from datetime import datetime
from khala.application.services.adaptive_search_tuner import AdaptiveSearchTuner, SearchFeedback
from khala.infrastructure.surrealdb.client import SurrealDBClient

class TestAdaptiveSearchTuner(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock(spec=SurrealDBClient)
        self.mock_db.create = AsyncMock()
        self.mock_db.query = AsyncMock()
        self.tuner = AdaptiveSearchTuner(self.mock_db)

    def test_record_feedback(self):
        feedback = SearchFeedback(
            query="test query",
            result_ids=["mem:1", "mem:2"],
            user_id="user_1",
            agent_id="agent_1",
            success=True
        )

        asyncio.run(self.tuner.record_feedback(feedback))

        self.mock_db.create.assert_called_once()
        args = self.mock_db.create.call_args
        self.assertEqual(args[0][0], "search_feedback")
        self.assertEqual(args[0][1]["success"], True)
        self.assertEqual(args[0][1]["query"], "test query")

    def test_get_tuned_parameters_defaults(self):
        # Should return defaults when cache is empty and DB is mocked (or returns nothing)
        params = asyncio.run(self.tuner.get_tuned_parameters("agent_1", "user_1"))
        self.assertEqual(params["alpha"], 0.5)
        self.assertEqual(params["limit"], 10)

    def test_tune_online_jitter(self):
        # Test that it returns a valid float between 0 and 1
        new_alpha = asyncio.run(self.tuner.tune_online("query", 0.5))
        self.assertTrue(0.0 <= new_alpha <= 1.0)

if __name__ == "__main__":
    unittest.main()
