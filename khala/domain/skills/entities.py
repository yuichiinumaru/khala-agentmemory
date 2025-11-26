"""Core domain entities for the skill system.

These entities represent executable capabilities within the system.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid

from ..memory.value_objects import EmbeddingVector
from .value_objects import SkillParameter, SkillType, SkillLanguage

@dataclass
class Skill:
    """Entity representing an executable skill."""
    
    name: str
    description: str
    code: str
    language: SkillLanguage
    skill_type: SkillType
    
    # Optional attributes
    parameters: List[SkillParameter] = field(default_factory=list)
    return_type: str = "Any"
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Identity and Search
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    embedding: Optional[EmbeddingVector] = field(default=None)
    
    # Lifecycle
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: str = "1.0.0"
    is_active: bool = True
    
    def __post_init__(self) -> None:
        """Validate skill entity."""
        if not self.name.strip():
            raise ValueError("Skill name cannot be empty")
        
        if not self.description.strip():
            raise ValueError("Skill description cannot be empty")
            
        if not self.code.strip():
            raise ValueError("Skill code cannot be empty")
    
    def update_code(self, new_code: str, new_version: Optional[str] = None) -> None:
        """Update the skill code and version."""
        if not new_code.strip():
            raise ValueError("New code cannot be empty")
            
        self.code = new_code
        self.updated_at = datetime.now(timezone.utc)
        
        if new_version:
            self.version = new_version
            
    def add_tag(self, tag: str) -> None:
        """Add a tag to the skill."""
        if tag and tag.strip() not in self.tags:
            self.tags.append(tag.strip())
            self.updated_at = datetime.now(timezone.utc)
