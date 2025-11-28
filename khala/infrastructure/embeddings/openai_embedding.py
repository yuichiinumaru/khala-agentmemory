from typing import List
import os
import logging
from openai import AsyncOpenAI

from khala.domain.ports.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class OpenAIEmbedding(EmbeddingService):
    """OpenAI implementation of EmbeddingService."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str = None):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model

    async def get_embedding(self, text: str) -> List[float]:
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
