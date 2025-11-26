"""Domain services for instruction registry."""

import logging
from typing import List, Dict, Optional, Any
from string import Template

from .entities import Instruction, InstructionSet, InstructionType

logger = logging.getLogger(__name__)

class InstructionRegistry:
    """Service for managing and compiling instructions."""
    
    def __init__(self):
        self._instructions: Dict[str, Instruction] = {}
        self._sets: Dict[str, InstructionSet] = {}
        
    def register_instruction(self, instruction: Instruction) -> None:
        """Register a new instruction."""
        self._instructions[instruction.id] = instruction
        logger.info(f"Registered instruction: {instruction.name} ({instruction.id})")
        
    def get_instruction(self, instruction_id: str) -> Optional[Instruction]:
        """Get an instruction by ID."""
        return self._instructions.get(instruction_id)
        
    def create_instruction_set(self, set_id: str, name: str, instruction_ids: List[str]) -> InstructionSet:
        """Create a set of instructions."""
        instructions = []
        for i_id in instruction_ids:
            instr = self.get_instruction(i_id)
            if instr:
                instructions.append(instr)
            else:
                logger.warning(f"Instruction {i_id} not found when creating set {name}")
                
        instruction_set = InstructionSet(
            id=set_id,
            name=name,
            description=f"Set of {len(instructions)} instructions",
            instructions=instructions
        )
        self._sets[set_id] = instruction_set
        return instruction_set
        
    def compile_prompt(self, set_id: str, variables: Dict[str, Any]) -> str:
        """Compile an instruction set into a final prompt."""
        instruction_set = self._sets.get(set_id)
        if not instruction_set:
            raise ValueError(f"Instruction set {set_id} not found")
            
        compiled_parts = []
        
        # Sort by type priority: SYSTEM -> PERSONA -> CONSTRAINT -> TASK -> FORMAT
        priority = {
            InstructionType.SYSTEM: 0,
            InstructionType.PERSONA: 1,
            InstructionType.CONSTRAINT: 2,
            InstructionType.TASK: 3,
            InstructionType.FORMAT: 4
        }
        
        sorted_instructions = sorted(
            instruction_set.instructions, 
            key=lambda x: priority.get(x.instruction_type, 99)
        )
        
        for instr in sorted_instructions:
            try:
                # Simple template substitution
                template = Template(instr.content)
                # Only provide variables that are present in the template to avoid errors?
                # Template.safe_substitute might be better
                part = template.safe_substitute(variables)
                compiled_parts.append(part)
            except Exception as e:
                logger.error(f"Error compiling instruction {instr.id}: {e}")
                compiled_parts.append(instr.content) # Fallback to raw content
                
        return "\n\n".join(compiled_parts)
