
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock
import os

# Add project root
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../..")))

# Global mocks
sys.modules["surrealdb"] = MagicMock()
sys.modules["surrealdb.data"] = MagicMock()
sys.modules["surrealdb.data.types"] = MagicMock()
sys.modules["surrealdb.data.types.geometry"] = MagicMock()
sys.modules["numpy"] = MagicMock()
sys.modules["google"] = MagicMock()
sys.modules["google.generativeai"] = MagicMock()
sys.modules["google.ai"] = MagicMock()
sys.modules["google.ai.generativelanguage"] = MagicMock()

mock_gemini_module = MagicMock()
mock_gemini_module.GeminiClient = MagicMock
sys.modules["khala.infrastructure.gemini.client"] = mock_gemini_module

from khala.application.services.explainability_service import ExplainabilityService
from khala.infrastructure.surrealdb.client import SurrealDBClient

class TestExplainabilityService(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.mock_db_client = MagicMock(spec=SurrealDBClient)
        self.mock_db_client.get_connection = MagicMock()
        self.conn_mock = AsyncMock()
        self.mock_db_client.get_connection.return_value.__aenter__.return_value = self.conn_mock
        self.mock_db_client.get_connection.return_value.__aexit__.return_value = None

        self.service = ExplainabilityService(self.mock_db_client)

    async def test_store_reasoning_path(self):
        # Setup mock return
        self.conn_mock.query.return_value = [{"result": [{"id": "path:123"}]}]

        result = await self.service.store_reasoning_path(
            query_entity="ent:1",
            target_entity="ent:2",
            path=[{"node": "ent:1"}, {"node": "ent:2"}],
            llm_explanation="Because X",
            confidence=0.9,
            final_rank=1
        )

        self.assertEqual(result, "path:123")
        self.conn_mock.query.assert_called_once()
        args, kwargs = self.conn_mock.query.call_args

        # Check positional args
        self.assertIn("CREATE reasoning_paths", args[0])
        self.assertEqual(args[1]['query_entity'], "ent:1")
        self.assertEqual(args[1]['confidence'], 0.9)

    async def test_get_reasoning_paths(self):
        self.conn_mock.query.return_value = [{"result": [{"id": "path:123", "query_entity": "ent:1"}]}]

        paths = await self.service.get_reasoning_paths(query_entity="ent:1")

        self.assertEqual(len(paths), 1)
        self.assertEqual(paths[0]["id"], "path:123")
        self.conn_mock.query.assert_called_once()

        args, kwargs = self.conn_mock.query.call_args
        self.assertIn("SELECT * FROM reasoning_paths", args[0])
        self.assertEqual(args[1]['query_entity'], "ent:1")

if __name__ == "__main__":
    unittest.main()
