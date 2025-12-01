from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from .entities import Memory, Relationship
from .value_objects import EmbeddingVector

class MemoryRepository(ABC):
    """
    Abstract interface for memory persistence.
    Decouples the domain from the specific database implementation.
    """
    
    @abstractmethod
    async def create(self, memory: Memory) -> str:
        """Save a new memory."""
        pass
        
    @abstractmethod
    async def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by its ID."""
        pass
        
    @abstractmethod
    async def update(self, memory: Memory) -> None:
        """Update an existing memory."""
        pass
        
    @abstractmethod
    async def delete(self, memory_id: str) -> None:
        """Delete a memory."""
        pass
        
    @abstractmethod
    async def search_by_vector(
        self, 
        embedding: EmbeddingVector, 
        user_id: str, 
        top_k: int = 10, 
        min_similarity: float = 0.6,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Memory]:
        """Search memories by vector similarity."""
        pass
        
    @abstractmethod
    async def search_by_text(
        self, 
        query_text: str, 
        user_id: str, 
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Memory]:
        """Search memories by text (BM25/Full-text)."""
        pass
        
    @abstractmethod
    async def get_by_tier(
        self, 
        user_id: str, 
        tier: str, 
        limit: int = 100
    ) -> List[Memory]:
        """Retrieve memories by tier."""
        pass

    @abstractmethod
    async def get_relationships(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 1000
    ) -> List[Relationship]:
        """Retrieve relationships based on filters."""
        pass
