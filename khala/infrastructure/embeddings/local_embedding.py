from typing import List
import logging

from khala.domain.ports.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class LocalEmbedding(EmbeddingService):
    """Local implementation of EmbeddingService using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed. LocalEmbedding will fail.")
            self.model = None

    async def get_embedding(self, text: str) -> List[float]:
        if not self.model:
            raise ImportError("sentence-transformers is not installed")

        # sentence-transformers is synchronous, so we might want to run this in an executor
        # but for simplicity in this stub/implementation we call it directly.
        # Ideally: await loop.run_in_executor(None, self.model.encode, text)
        import asyncio
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(None, self.model.encode, text)
        return embedding.tolist()

    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        if not self.model:
            raise ImportError("sentence-transformers is not installed")

        import asyncio
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(None, self.model.encode, texts)
        return embeddings.tolist()
