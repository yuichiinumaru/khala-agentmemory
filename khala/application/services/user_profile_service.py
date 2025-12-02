from typing import Optional, Dict, Any, List
import logging
from datetime import datetime, timezone

from khala.domain.user.entities import UserProfile
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class UserProfileService:
    """Service for managing user profiles and preferences (Strategy 154)."""

    def __init__(self, db_client: Optional[SurrealDBClient] = None):
        self.db_client = db_client or SurrealDBClient()
        self.table = "user_profile"

    async def get_profile(self, user_id: str) -> Optional[UserProfile]:
        """
        Get user profile by user ID.

        Args:
            user_id: The unique user identifier.

        Returns:
            UserProfile if found, None otherwise.
        """
        try:
            # Query by user_id
            query = f"SELECT * FROM {self.table} WHERE user_id = $user_id LIMIT 1"
            params = {"user_id": user_id}

            async with self.db_client.get_connection() as conn:
                results = await conn.query(query, params)

                # Check results structure (SurrealDB returns list of results)
                if results and isinstance(results, list):
                     # The actual result data is usually in the first element's 'result'
                     # or directly if it's a simple select
                     data = results[0]
                     if isinstance(data, dict) and 'result' in data:
                         items = data['result']
                         if items:
                             return UserProfile.from_dict(items[0])
                     elif isinstance(data, list) and data:
                          return UserProfile.from_dict(data[0]) # Direct list return
                     elif isinstance(data, dict) and 'user_id' in data:
                          return UserProfile.from_dict(data)

            return None

        except Exception as e:
            logger.error(f"Failed to get profile for user {user_id}: {e}")
            raise

    async def create_or_update_profile(
        self,
        user_id: str,
        preferences: Optional[Dict[str, Any]] = None,
        context: Optional[Dict[str, Any]] = None,
        traits: Optional[List[str]] = None
    ) -> UserProfile:
        """
        Create or update a user profile.

        Args:
            user_id: The user ID.
            preferences: Dictionary of preferences to merge.
            context: Dictionary of context to merge.
            traits: List of traits to replace or append.

        Returns:
            The updated UserProfile.
        """
        try:
            existing = await self.get_profile(user_id)

            if existing:
                # Update existing
                if preferences:
                    existing.preferences.update(preferences)
                if context:
                    existing.context.update(context)
                if traits:
                    # Append unique traits
                    existing.traits = list(set(existing.traits + traits))

                existing.updated_at = datetime.now(timezone.utc)

                # Persist update
                # We need the record ID for update, or use UPDATE ... SET ... WHERE user_id = ...
                query = f"""
                UPDATE {self.table} SET
                    preferences = $preferences,
                    context = $context,
                    traits = $traits,
                    updated_at = $updated_at
                WHERE user_id = $user_id
                """
                params = {
                    "user_id": user_id,
                    "preferences": existing.preferences,
                    "context": existing.context,
                    "traits": existing.traits,
                    "updated_at": existing.updated_at.isoformat()
                }

                async with self.db_client.get_connection() as conn:
                    await conn.query(query, params)

                return existing

            else:
                # Create new
                profile = UserProfile(
                    user_id=user_id,
                    preferences=preferences or {},
                    context=context or {},
                    traits=traits or []
                )

                # Insert
                query = f"CREATE {self.table} CONTENT $content"
                params = {"content": profile.to_dict()}

                async with self.db_client.get_connection() as conn:
                    result = await conn.query(query, params)
                    # Extract ID if needed, but we return the object
                    if result and isinstance(result, list) and result[0].get('result'):
                         profile.id = result[0]['result'][0]['id']

                return profile

        except Exception as e:
            logger.error(f"Failed to update profile for user {user_id}: {e}")
            raise

    async def set_preference(self, user_id: str, key: str, value: Any) -> UserProfile:
        """Set a specific preference value."""
        return await self.create_or_update_profile(user_id, preferences={key: value})

    async def get_preference(self, user_id: str, key: str, default: Any = None) -> Any:
        """Get a specific preference value."""
        profile = await self.get_profile(user_id)
        if profile:
            return profile.preferences.get(key, default)
        return default
