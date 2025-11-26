"""Value objects for hypothesis domain."""

from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime, timezone
from typing import Optional, Dict, Any

class HypothesisStatus(Enum):
    """Status of a hypothesis."""
    PROPOSED = "proposed"
    TESTING = "testing"
    VALIDATED = "validated"
    REJECTED = "rejected"
    INCONCLUSIVE = "inconclusive"

class EvidenceType(Enum):
    """Type of evidence."""
    OBSERVATION = "observation"
    EXPERIMENT = "experiment"
    LOGICAL_DEDUCTION = "logical_deduction"
    EXTERNAL_SOURCE = "external_source"

@dataclass
class Evidence:
    """Evidence supporting or contradicting a hypothesis."""
    content: str
    evidence_type: EvidenceType
    confidence_score: float  # 0.0 to 1.0
    source_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        if not 0.0 <= self.confidence_score <= 1.0:
            raise ValueError("Confidence score must be between 0.0 and 1.0")
