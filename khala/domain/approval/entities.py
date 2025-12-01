from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, Any, Optional
import uuid

class ApprovalStatus(Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    FAILED = "failed"
    COMPLETED = "completed"

class ApprovalActionType(Enum):
    MEMORY_CONSOLIDATION = "memory_consolidation"
    MEMORY_DELETION = "memory_deletion"
    CRITICAL_CONFIG_CHANGE = "critical_config_change"

@dataclass
class ApprovalRequest:
    """Represents a request for human approval."""

    user_id: str
    action_type: ApprovalActionType
    payload: Dict[str, Any]
    description: str

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: ApprovalStatus = ApprovalStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    reviewer_id: Optional[str] = None
    rejection_reason: Optional[str] = None

    def approve(self, reviewer_id: Optional[str] = None) -> None:
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot approve request in status {self.status}")
        self.status = ApprovalStatus.APPROVED
        self.reviewed_at = datetime.now(timezone.utc)
        self.reviewer_id = reviewer_id
        self.updated_at = self.reviewed_at

    def reject(self, reason: str, reviewer_id: Optional[str] = None) -> None:
        if self.status != ApprovalStatus.PENDING:
            raise ValueError(f"Cannot reject request in status {self.status}")
        self.status = ApprovalStatus.REJECTED
        self.rejection_reason = reason
        self.reviewed_at = datetime.now(timezone.utc)
        self.reviewer_id = reviewer_id
        self.updated_at = self.reviewed_at

    def complete(self) -> None:
        if self.status != ApprovalStatus.APPROVED:
             raise ValueError(f"Cannot complete request in status {self.status}")
        self.status = ApprovalStatus.COMPLETED
        self.updated_at = datetime.now(timezone.utc)

    def fail(self, reason: str) -> None:
        self.status = ApprovalStatus.FAILED
        self.rejection_reason = reason
        self.updated_at = datetime.now(timezone.utc)
