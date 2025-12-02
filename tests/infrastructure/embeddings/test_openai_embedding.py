import unittest
from unittest.mock import AsyncMock, patch, MagicMock
from khala.infrastructure.embeddings.openai_embedding import OpenAIEmbedding
from khala.domain.memory.value_objects import EmbeddingVector

class TestOpenAIEmbedding(unittest.IsolatedAsyncioTestCase):
    async def test_get_embedding_returns_vector_object(self):
        with patch('khala.infrastructure.embeddings.openai_embedding.AsyncOpenAI') as mock_openai:
            # Setup mock response
            mock_client = mock_openai.return_value
            mock_response = MagicMock()
            mock_response.data = [MagicMock(embedding=[0.1, 0.2, 0.3])]
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            service = OpenAIEmbedding(api_key="fake")
            embedding = await service.get_embedding("test")

            self.assertIsInstance(embedding, EmbeddingVector)
            self.assertEqual(embedding.values, [0.1, 0.2, 0.3])
            self.assertEqual(embedding.model, "text-embedding-3-small")
            self.assertEqual(embedding.version, "v1")

    async def test_get_embeddings_returns_list_of_vector_objects(self):
        with patch('khala.infrastructure.embeddings.openai_embedding.AsyncOpenAI') as mock_openai:
            mock_client = mock_openai.return_value
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=[0.1, 0.2]),
                MagicMock(embedding=[0.3, 0.4])
            ]
            mock_client.embeddings.create = AsyncMock(return_value=mock_response)

            service = OpenAIEmbedding(api_key="fake")
            embeddings = await service.get_embeddings(["t1", "t2"])

            self.assertEqual(len(embeddings), 2)
            self.assertIsInstance(embeddings[0], EmbeddingVector)
            self.assertEqual(embeddings[0].values, [0.1, 0.2])
            self.assertEqual(embeddings[1].values, [0.3, 0.4])

if __name__ == '__main__':
    unittest.main()
