"""Domain entities for Standard Operating Procedures (SOPs)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

@dataclass
class SOPStep:
    """A single step in an SOP."""
    order: int
    description: str
    expected_output: str
    required_tools: List[str] = field(default_factory=list)
    required_skills: List[str] = field(default_factory=list)
    estimated_time_minutes: int = 5

@dataclass
class SOP:
    """Standard Operating Procedure definition."""
    id: str
    title: str
    objective: str
    steps: List[SOPStep]
    triggers: List[str] = field(default_factory=list) # Natural language triggers
    owner_role: str = "worker"
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    version: str = "1.0.0"
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True
