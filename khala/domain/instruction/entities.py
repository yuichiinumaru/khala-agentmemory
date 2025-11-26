"""Domain entities for instruction registry."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional

class InstructionType(Enum):
    """Type of instruction."""
    SYSTEM = "system"       # Core system behavior
    PERSONA = "persona"     # Agent personality/role
    TASK = "task"           # Specific task guidelines
    FORMAT = "format"       # Output formatting rules
    CONSTRAINT = "constraint" # Safety or operational constraints

@dataclass
class Instruction:
    """An instruction or prompt template."""
    id: str
    name: str
    content: str  # The prompt text (can be a template)
    instruction_type: InstructionType
    version: str = "1.0.0"
    variables: List[str] = field(default_factory=list)  # Variables in the template
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

@dataclass
class InstructionSet:
    """A collection of instructions forming a complete context."""
    id: str
    name: str
    description: str
    instructions: List[Instruction]
    target_agent_role: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
