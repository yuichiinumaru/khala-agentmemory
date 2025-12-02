from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from datetime import datetime

class FlowStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"

class StepType(Enum):
    ACTION = "action"     # Executes a function
    DECISION = "decision" # Returns the next step name based on logic
    AGENT = "agent"       # Delegates to an agent

@dataclass
class FlowContext:
    """Shared state for a flow execution."""
    flow_id: str
    data: Dict[str, Any] = field(default_factory=dict)
    history: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class FlowStep:
    name: str
    step_type: StepType
    handler: str  # Name of the function or agent to execute
    next_step: Optional[str] = None  # Default next step
    config: Dict[str, Any] = field(default_factory=dict)

@dataclass
class Flow:
    id: str
    name: str
    steps: Dict[str, FlowStep]
    start_step: str
    description: str = ""

@dataclass
class FlowExecution:
    id: str
    flow_id: str
    status: FlowStatus
    current_step: Optional[str]
    context: FlowContext
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    error: Optional[str] = None
