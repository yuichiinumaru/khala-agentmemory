"""Core entities for Deterministic Flows (Strategy 116).

Flows represent structured, deterministic sequences of actions (SOPs),
distinct from autonomous Crews.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid

@dataclass
class FlowStep:
    """A single step in a deterministic flow."""
    name: str
    description: str
    tool: str
    parameters: Dict[str, Any] = field(default_factory=dict)
    required_output: Optional[str] = None
    retry_count: int = 0
    timeout_seconds: int = 60

@dataclass
class Flow:
    """A deterministic workflow definition."""
    name: str
    description: str
    steps: List[FlowStep]
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    is_active: bool = True

@dataclass
class FlowExecution:
    """An instance of a flow execution."""
    flow_id: str
    user_id: str
    status: str = "pending" # pending, running, completed, failed
    current_step_index: int = 0
    context: Dict[str, Any] = field(default_factory=dict)
    results: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None
