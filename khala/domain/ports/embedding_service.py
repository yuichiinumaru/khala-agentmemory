from abc import ABC, abstractmethod
from typing import List, Union
from khala.domain.memory.value_objects import EmbeddingVector

class EmbeddingService(ABC):
    """Interface for embedding services."""

    @abstractmethod
    async def get_embedding(self, text: str) -> EmbeddingVector:
        """Generate embedding for a single text string."""
        pass

    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[EmbeddingVector]:
        """Generate embeddings for a list of text strings."""
        pass
