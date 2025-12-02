from typing import List
import logging

from khala.domain.ports.embedding_service import EmbeddingService
from khala.domain.memory.value_objects import EmbeddingVector

logger = logging.getLogger(__name__)

class LocalEmbedding(EmbeddingService):
    """Local implementation of EmbeddingService using sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        try:
            from sentence_transformers import SentenceTransformer
            self.model = SentenceTransformer(model_name)
        except ImportError:
            logger.warning("sentence-transformers not installed. LocalEmbedding will fail.")
            self.model = None

    async def get_embedding(self, text: str) -> EmbeddingVector:
        if not self.model:
            raise ImportError("sentence-transformers is not installed")

        import asyncio
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(None, self.model.encode, text)
        return EmbeddingVector(
            values=embedding.tolist(),
            model=self.model_name,
            version="v1"
        )

    async def get_embeddings(self, texts: List[str]) -> List[EmbeddingVector]:
        if not self.model:
            raise ImportError("sentence-transformers is not installed")

        import asyncio
        loop = asyncio.get_running_loop()
        embeddings = await loop.run_in_executor(None, self.model.encode, texts)
        return [
            EmbeddingVector(
                values=emb.tolist(),
                model=self.model_name,
                version="v1"
            ) for emb in embeddings
        ]
