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

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "user_id": self.user_id,
            "action": self.action,
            "target_id": self.target_id,
            "target_type": self.target_type,
            "details": self.details,
            "timestamp": self.timestamp.isoformat()
        }
