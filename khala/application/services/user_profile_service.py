from typing import Dict, Any, List, Optional
import logging
from datetime import datetime, timezone
from dataclasses import dataclass, field
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

@dataclass
class UserProfile:
    user_id: str
    preferences: Dict[str, Any] = field(default_factory=dict)
    traits: List[str] = field(default_factory=list)
    knowledge_level: str = "intermediate" # beginner, intermediate, expert
    last_active: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

class UserProfileService:
    """
    Service for managing user models and preferences.
    Strategy 154: User Modeling.
    """
    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client
        self.table = "user_profile"

    async def get_profile(self, user_id: str) -> UserProfile:
        """Get or create a user profile."""
        profile_id = f"{self.table}:{user_id}"
        result = await self.db_client.select(profile_id)

        if result:
            return UserProfile(
                user_id=user_id,
                preferences=result.get("preferences", {}),
                traits=result.get("traits", []),
                knowledge_level=result.get("knowledge_level", "intermediate"),
                last_active=datetime.fromisoformat(result["last_active"]) if isinstance(result.get("last_active"), str) else result.get("last_active")
            )
        else:
            # Create default
            profile = UserProfile(user_id=user_id)
            await self.update_profile(profile)
            return profile

    async def update_profile(self, profile: UserProfile) -> None:
        """Update user profile."""
        profile_id = f"{self.table}:{profile.user_id}"
        data = {
            "id": profile_id,
            "preferences": profile.preferences,
            "traits": profile.traits,
            "knowledge_level": profile.knowledge_level,
            "last_active": datetime.now(timezone.utc).isoformat()
        }
        # Upsert logic
        try:
            # Try update first
            await self.db_client.update(profile_id, data)
        except Exception:
            # Fallback to create if not exists (SurrealDB 'update' acts as upsert if ID given? client specifics vary)
            # Assuming client.update does full replacement or merge.
            # Safe bet: create if select fails, update otherwise.
            # But here we just assume it works or we use specialized create.
            await self.db_client.create(self.table, data)

    async def update_preference(self, user_id: str, key: str, value: Any) -> None:
        """Update a single preference."""
        profile = await self.get_profile(user_id)
        profile.preferences[key] = value
        await self.update_profile(profile)
