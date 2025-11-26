"""Value objects for the skill domain.

Immutable value objects that represent concepts in the skill system.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Any, Dict
from enum import Enum

@dataclass(frozen=True)
class SkillParameter:
    """Definition of a parameter for a skill."""
    
    name: str
    type: str
    description: str
    required: bool = True
    default_value: Optional[Any] = None
    
    def __post_init__(self) -> None:
        """Validate parameter definition."""
        if not self.name.strip():
            raise ValueError("Parameter name cannot be empty")
        if not self.type.strip():
            raise ValueError("Parameter type cannot be empty")

class SkillType(Enum):
    """Type of skill execution model."""
    
    ATOMIC = "atomic"       # Single function/script
    COMPOSITE = "composite" # Chain or sequence of other skills
    PIPELINE = "pipeline"   # Complex pipeline with data flow

class SkillLanguage(Enum):
    """Programming language of the skill."""
    
    PYTHON = "python"
    SQL = "sql"
    SHELL = "shell"
    NATURAL_LANGUAGE = "natural_language" # Prompt/Instruction
