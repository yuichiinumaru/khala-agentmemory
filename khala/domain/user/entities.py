from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime, timezone

@dataclass
class UserProfile:
    """Domain entity representing a user's profile and preferences."""

    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    context: Dict[str, Any] = field(default_factory=dict)
    traits: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "user_id": self.user_id,
            "preferences": self.preferences,
            "context": self.context,
            "traits": self.traits,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create from dictionary."""
        return cls(
            id=data.get("id"),
            user_id=data["user_id"],
            preferences=data.get("preferences", {}),
            context=data.get("context", {}),
            traits=data.get("traits", []),
            created_at=datetime.fromisoformat(data.get("created_at", datetime.now(timezone.utc).isoformat())),
            updated_at=datetime.fromisoformat(data.get("updated_at", datetime.now(timezone.utc).isoformat()))
        )
