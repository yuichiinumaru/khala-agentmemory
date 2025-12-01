import unittest
from unittest.mock import AsyncMock, MagicMock
from khala.infrastructure.background.jobs.vector_drift_job import VectorDriftJob

class TestVectorDriftJob(unittest.IsolatedAsyncioTestCase):

    async def test_execute_no_memories(self):
        db_client = MagicMock()
        db_client.get_connection = MagicMock()
        conn = AsyncMock()
        conn.query.return_value = []
        db_client.get_connection.return_value.__aenter__.return_value = conn

        embedding_service = MagicMock()

        job = VectorDriftJob(db_client, embedding_service)
        result = await job.execute({})

        self.assertEqual(result["processed"], 0)
        self.assertEqual(result["message"], "No memories found with embeddings.")

    async def test_execute_drift_detection(self):
        db_client = MagicMock()
        db_client.get_connection = MagicMock()
        conn = AsyncMock()

        # Mock memories
        # Memory 1: Identical embedding
        # Memory 2: Different embedding (drift)
        memories = [
            {"id": "mem1", "content": "text1", "embedding": [1.0, 0.0]},
            {"id": "mem2", "content": "text2", "embedding": [0.0, 1.0]}
        ]

        # SurrealDB response structure
        conn.query.return_value = [{"result": memories}]
        db_client.get_connection.return_value.__aenter__.return_value = conn

        embedding_service = MagicMock()
        # New embeddings
        # For mem1: [1.0, 0.0] -> sim = 1.0
        # For mem2: [1.0, 0.0] -> sim = 0.0 (high drift)
        embedding_service.get_embedding = AsyncMock(side_effect=[
            [1.0, 0.0],
            [1.0, 0.0]
        ])

        job = VectorDriftJob(db_client, embedding_service)
        result = await job.execute({"sample_size": 10})

        self.assertEqual(result["processed"], 2)
        self.assertEqual(result["drift_count"], 1) # mem2 drifted
        self.assertTrue(result["drift_detected"])
        self.assertEqual(result["max_drift_mem_id"], "mem2")

    async def test_execute_error_handling(self):
        db_client = MagicMock()
        db_client.get_connection = MagicMock()
        conn = AsyncMock()
        conn.query.side_effect = Exception("DB Error")
        db_client.get_connection.return_value.__aenter__.return_value = conn

        embedding_service = MagicMock()

        job = VectorDriftJob(db_client, embedding_service)
        result = await job.execute({})

        self.assertIn("error", result)
        self.assertEqual(result["processed"], 0)

if __name__ == '__main__':
    unittest.main()
