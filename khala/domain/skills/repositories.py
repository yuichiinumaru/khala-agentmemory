"""Repository interfaces for the skill domain."""

from abc import ABC, abstractmethod
from typing import List, Optional

from .entities import Skill
from ..memory.value_objects import EmbeddingVector

class SkillRepository(ABC):
    """Abstract repository for accessing skills."""
    
    @abstractmethod
    async def create(self, skill: Skill) -> str:
        """Save a new skill."""
        pass
        
    @abstractmethod
    async def get_by_id(self, skill_id: str) -> Optional[Skill]:
        """Retrieve a skill by its ID."""
        pass
        
    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Skill]:
        """Retrieve a skill by its name."""
        pass
        
    @abstractmethod
    async def update(self, skill: Skill) -> None:
        """Update an existing skill."""
        pass
        
    @abstractmethod
    async def delete(self, skill_id: str) -> None:
        """Delete a skill."""
        pass
        
    @abstractmethod
    async def search_by_vector(
        self, 
        embedding: EmbeddingVector, 
        top_k: int = 5, 
        min_similarity: float = 0.6
    ) -> List[Skill]:
        """Search skills by vector similarity."""
        pass
        
    @abstractmethod
    async def search_by_text(
        self, 
        query_text: str, 
        top_k: int = 5
    ) -> List[Skill]:
        """Search skills by text (BM25/Full-text)."""
        pass
