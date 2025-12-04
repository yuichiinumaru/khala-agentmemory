"""Core entities for Autonomous Crews (Strategy 116).

Crews represent groups of autonomous agents working together dynamically,
distinct from deterministic Flows.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

class CrewRole(Enum):
    LEADER = "leader"
    RESEARCHER = "researcher"
    WRITER = "writer"
    CRITIC = "critic"
    EXECUTOR = "executor"

@dataclass
class AgentMember:
    """An agent member of a crew."""
    agent_id: str
    role: CrewRole
    capabilities: List[str]
    description: str

@dataclass
class Crew:
    """A team of autonomous agents."""
    name: str
    objective: str
    members: List[AgentMember]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    manager_agent_id: Optional[str] = None
    memory_context_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "active"

@dataclass
class CrewTask:
    """A high-level objective assigned to a crew."""
    crew_id: str
    description: str
    expected_outcome: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    assigned_to_member: Optional[str] = None
    status: str = "pending"
    result: Optional[str] = None
