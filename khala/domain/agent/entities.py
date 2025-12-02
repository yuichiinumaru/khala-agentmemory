"""Domain entities for agent coordination."""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import List, Dict, Any, Optional

class AgentStatus(Enum):
    """Status of an agent."""
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"

class AgentRole(Enum):
    """Role of an agent in the system."""
    WORKER = "worker"
    MANAGER = "manager"
    REVIEWER = "reviewer"
    SPECIALIST = "specialist"

@dataclass
class AgentProfile:
    """Profile information for an agent."""
    id: str
    name: str
    role: AgentRole
    capabilities: List[str]
    negative_constraints: List[str] = field(default_factory=list)
    status: AgentStatus = AgentStatus.IDLE
    metadata: Dict[str, Any] = field(default_factory=dict)
    last_heartbeat: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class AgentMessage:
    """Message exchanged between agents."""
    id: str
    sender_id: str
    recipient_id: str  # "all" for broadcast
    content: str
    message_type: str  # "task", "response", "alert", "coordination"
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
