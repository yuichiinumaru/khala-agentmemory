"""Repository interface for hypotheses."""

from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import Hypothesis

class HypothesisRepository(ABC):
    """Interface for hypothesis storage."""
    
    @abstractmethod
    def save(self, hypothesis: Hypothesis) -> None:
        """Save a hypothesis."""
        pass
    
    @abstractmethod
    def find_by_id(self, hypothesis_id: str) -> Optional[Hypothesis]:
        """Find a hypothesis by ID."""
        pass
    
    @abstractmethod
    def find_all(self) -> List[Hypothesis]:
        """Find all hypotheses."""
        pass
