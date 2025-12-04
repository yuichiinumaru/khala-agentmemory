from abc import ABC, abstractmethod
from typing import List, Optional
from khala.domain.instruction.entities import Instruction, InstructionType

class InstructionRepository(ABC):
    """
    Interface for storing and retrieving instructions (prompts).
    Strategy 36: Instruction Registry.
    """

    @abstractmethod
    async def create(self, instruction: Instruction) -> Instruction:
        """Create a new instruction."""
        pass

    @abstractmethod
    async def get_by_id(self, instruction_id: str) -> Optional[Instruction]:
        """Get an instruction by its ID."""
        pass

    @abstractmethod
    async def get_by_name(self, name: str) -> Optional[Instruction]:
        """Get an instruction by name."""
        pass

    @abstractmethod
    async def search(self, query: str, limit: int = 10) -> List[Instruction]:
        """Search instructions by text content."""
        pass

    @abstractmethod
    async def get_by_type(self, instruction_type: InstructionType) -> List[Instruction]:
        """Get all instructions of a certain type."""
        pass

    @abstractmethod
    async def update(self, instruction: Instruction) -> Instruction:
        """Update an existing instruction."""
        pass

    @abstractmethod
    async def delete(self, instruction_id: str) -> bool:
        """Delete an instruction."""
        pass
