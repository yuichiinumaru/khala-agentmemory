from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional

class SubagentRole(Enum):
    """Specialized roles for Gemini subagents."""
    ANALYZER = "analyzer"
    SYNTHESIZER = "synthesizer"
    CURATOR = "curator"
    RESEARCHER = "researcher"
    VALIDATOR = "validator"
    CONSOLIDATOR = "consolidator"
    EXTRACTOR = "extractor"
    OPTIMIZER = "optimizer"

class TaskPriority(Enum):
    """Task priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4

class ModelTier(Enum):
    """Model performance tiers for cascading."""
    FAST = "fast"          # Gemini 2.5 Flash
    BALANCED = "balanced"  # Gemini 2.5 Pro
    REASONING = "reasoning" # Gemini 2.5 Pro (High Temp/Thinking)

@dataclass
class SubagentTask:
    """Task definition for subagent execution."""
    task_id: str
    role: SubagentRole
    priority: TaskPriority
    task_type: str
    input_data: Dict[str, Any]
    context: Dict[str, Any]
    model_tier: ModelTier = ModelTier.BALANCED
    expected_output: Optional[str] = None
    timeout_seconds: int = 60
    max_retries: int = 2
    created_at: datetime = None
    
    def __post_init__(self):
        if self.created_at is None:
            self.created_at = datetime.now(timezone.utc)

@dataclass
class SubagentResult:
    """Result from subagent task execution."""
    task_id: str
    role: SubagentRole
    success: bool
    output: Any
    reasoning: str
    confidence_score: float
    execution_time_ms: float
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    completed_at: datetime = None
    
    def __post_init__(self):
        if self.completed_at is None:
            self.completed_at = datetime.now(timezone.utc)
