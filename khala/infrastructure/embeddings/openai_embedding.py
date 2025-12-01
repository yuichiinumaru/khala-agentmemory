from typing import List
import os
import logging
from openai import AsyncOpenAI

from khala.domain.ports.embedding_service import EmbeddingService
from khala.domain.memory.value_objects import EmbeddingVector

logger = logging.getLogger(__name__)

class OpenAIEmbedding(EmbeddingService):
    """OpenAI implementation of EmbeddingService."""

    def __init__(self, model: str = "text-embedding-3-small", api_key: str = None):
        self.client = AsyncOpenAI(api_key=api_key or os.getenv("OPENAI_API_KEY"))
        self.model = model
        self.dimensions = 1536 if model == "text-embedding-3-small" else None # Default or unknown

    async def get_embedding(self, text: str) -> EmbeddingVector:
        try:
            response = await self.client.embeddings.create(
                input=text,
                model=self.model
            )
            embedding_data = response.data[0].embedding
            return EmbeddingVector(
                values=embedding_data,
                model=self.model,
                version="v1" # OpenAI doesn't explicitly give version, but model name acts as one
            )
        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def get_embeddings(self, texts: List[str]) -> List[EmbeddingVector]:
        try:
            response = await self.client.embeddings.create(
                input=texts,
                model=self.model
            )
            return [
                EmbeddingVector(
                    values=data.embedding,
                    model=self.model,
                    version="v1"
                ) for data in response.data
            ]
        except Exception as e:
            logger.error(f"Error generating embeddings: {e}")
            raise
