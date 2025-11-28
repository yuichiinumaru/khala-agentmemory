from abc import ABC, abstractmethod
from typing import List, Union

class EmbeddingService(ABC):
    """Interface for embedding services."""

    @abstractmethod
    async def get_embedding(self, text: str) -> List[float]:
        """Generate embedding for a single text string."""
        pass

    @abstractmethod
    async def get_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of text strings."""
        pass
