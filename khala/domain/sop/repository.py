"""Repository interface for SOPs."""

from abc import ABC, abstractmethod
from typing import List, Optional
from .entities import SOP

class SOPRepository(ABC):
    """Abstract base class for SOP repository."""

    @abstractmethod
    async def create(self, sop: SOP) -> str:
        """Create a new SOP."""
        pass

    @abstractmethod
    async def get(self, sop_id: str) -> Optional[SOP]:
        """Get an SOP by ID."""
        pass

    @abstractmethod
    async def update(self, sop: SOP) -> None:
        """Update an existing SOP."""
        pass

    @abstractmethod
    async def list_active(self) -> List[SOP]:
        """List all active SOPs."""
        pass

    @abstractmethod
    async def search_by_trigger(self, trigger: str) -> List[SOP]:
        """Search SOPs by trigger phrase."""
        pass

    @abstractmethod
    async def search_by_tag(self, tag: str) -> List[SOP]:
        """Search SOPs by tag."""
        pass
