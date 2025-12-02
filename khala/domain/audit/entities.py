"""Audit domain entities."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

@dataclass
class AuditLog:
    """Audit log entry representing a system action."""

    user_id: str
    action: str
    target_id: str
    target_type: str  # 'memory', 'entity', 'relationship'
    details: Dict[str, Any] = field(default_factory=dict)

    # New fields matching schema more closely
    agent_id: Optional[str] = None
    operation: Optional[str] = None
    reason: Optional[str] = None
    before_state: Optional[Dict[str, Any]] = None
    after_state: Optional[Dict[str, Any]] = None

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self):
        """Set defaults."""
        if self.operation is None:
            self.operation = self.action

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        data = {
            "id": self.id,
            "user_id": self.user_id,
            # In schema 'action' is object, 'operation' is string.
            # We map self.action (str) to operation, and self.details to action (object) if needed?
            # Existing repo maps self.action to DB 'action'.
            # We will populate both 'action' (with details) and 'operation' (with action string)
            # to satisfy both legacy and new schema usage if possible.
            "action": self.details, # Using details as the flexible action object
            "target_id": self.target_id,
            "target_type": self.target_type,
            "details": self.details, # Keeping details for backward compat if query expects it
            "timestamp": self.timestamp.isoformat(),
            "agent_id": self.agent_id,
            "operation": self.operation or self.action,
            "reason": self.reason,
            "before_state": self.before_state,
            "after_state": self.after_state
        }

        # If target_type is memory, populate memory_id
        if self.target_type == "memory":
            data["memory_id"] = self.target_id

        return data
