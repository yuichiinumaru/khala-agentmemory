"""Repository interface for instruction registry."""

from abc import ABC, abstractmethod
from typing import List, Optional
from khala.domain.instruction.entities import Instruction, InstructionSet, InstructionType

class InstructionRepository(ABC):
    """Abstract repository for storing and retrieving instructions."""

    @abstractmethod
    async def create_instruction(self, instruction: Instruction) -> Instruction:
        """Create a new instruction."""
        pass

    @abstractmethod
    async def get_instruction(self, instruction_id: str) -> Optional[Instruction]:
        """Retrieve an instruction by ID."""
        pass

    @abstractmethod
    async def get_instruction_by_name(self, name: str, version: Optional[str] = None) -> Optional[Instruction]:
        """Retrieve an instruction by name and optional version."""
        pass

    @abstractmethod
    async def list_instructions(self, instruction_type: Optional[InstructionType] = None, tags: Optional[List[str]] = None) -> List[Instruction]:
        """List instructions, optionally filtering by type or tags."""
        pass

    @abstractmethod
    async def update_instruction(self, instruction: Instruction) -> Instruction:
        """Update an existing instruction."""
        pass

    @abstractmethod
    async def delete_instruction(self, instruction_id: str) -> bool:
        """Delete an instruction."""
        pass

    @abstractmethod
    async def create_instruction_set(self, instruction_set: InstructionSet) -> InstructionSet:
        """Create a new instruction set."""
        pass

    @abstractmethod
    async def get_instruction_set(self, set_id: str) -> Optional[InstructionSet]:
        """Retrieve an instruction set by ID."""
        pass

    @abstractmethod
    async def get_instruction_set_by_name(self, name: str) -> Optional[InstructionSet]:
        """Retrieve an instruction set by name."""
        pass
