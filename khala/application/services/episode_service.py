"""Episode Service for managing episodic memories.

This service handles the creation, retrieval, and management of episodes,
allowing for narrative threading and context grouping.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging
import uuid
from dataclasses import asdict

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.episode import Episode, EpisodeStatus
from khala.domain.memory.entities import Memory

logger = logging.getLogger(__name__)

class EpisodeService:
    """Service for managing episodes."""

    def __init__(self, db_client: Optional[SurrealDBClient] = None):
        """Initialize the service.

        Args:
            db_client: SurrealDB client instance (optional)
        """
        self.db_client = db_client or SurrealDBClient()

    async def create_episode(
        self,
        user_id: str,
        title: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        parent_episode_id: Optional[str] = None
    ) -> str:
        """Create a new episode.

        Args:
            user_id: ID of the user owner
            title: Title of the episode
            description: Optional description
            tags: Optional tags
            metadata: Optional metadata
            parent_episode_id: Optional parent episode ID

        Returns:
            ID of the created episode
        """
        episode = Episode(
            user_id=user_id,
            title=title,
            description=description,
            tags=tags or [],
            metadata=metadata or {},
            parent_episode_id=parent_episode_id
        )

        # Persist to DB
        # Since SurrealDBClient doesn't have create_episode method yet,
        # we'll implement a generic create or add it to client.
        # For now, let's execute raw query via client.

        query = """
        CREATE type::thing('episode', $id) CONTENT {
            user_id: $user_id,
            title: $title,
            description: $description,
            status: $status,
            started_at: $started_at,
            summary: $summary,
            metadata: $metadata,
            tags: $tags,
            memory_ids: $memory_ids,
            parent_episode_id: $parent_episode_id
        };
        """

        params = {
            "id": episode.id,
            "user_id": episode.user_id,
            "title": episode.title,
            "description": episode.description,
            "status": episode.status.value,
            "started_at": episode.started_at.isoformat(),
            "summary": episode.summary,
            "metadata": episode.metadata,
            "tags": episode.tags,
            "memory_ids": episode.memory_ids,
            "parent_episode_id": episode.parent_episode_id
        }

        async with self.db_client.get_connection() as conn:
            await conn.query(query, params)

        logger.info(f"Created episode {episode.id}: {episode.title}")
        return episode.id

    async def get_episode(self, episode_id: str) -> Optional[Episode]:
        """Retrieve an episode by ID."""
        query = "SELECT * FROM type::thing('episode', $id);"
        params = {"id": episode_id}

        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, params)

            if not response:
                return None

            if isinstance(response, list) and len(response) > 0:
                data = response[0]
                # Handle SurrealDB result wrapper
                if isinstance(data, dict) and 'result' in data:
                     if data['result']:
                         data = data['result'][0]
                     else:
                         return None

                # Helper to parse datetime
                def parse_dt(dt_val: Any) -> datetime:
                    if not dt_val:
                        return None
                    if isinstance(dt_val, str):
                        if dt_val.endswith('Z'):
                            dt_val = dt_val[:-1]
                        return datetime.fromisoformat(dt_val).replace(tzinfo=timezone.utc)
                    return dt_val

                # Strip 'episode:' prefix
                ep_id = data.get("id", episode_id)
                if isinstance(ep_id, str) and ep_id.startswith("episode:"):
                    ep_id = ep_id.split(":", 1)[1]

                return Episode(
                    id=ep_id,
                    user_id=data["user_id"],
                    title=data["title"],
                    description=data.get("description"),
                    status=EpisodeStatus(data["status"]),
                    started_at=parse_dt(data["started_at"]) or datetime.now(timezone.utc),
                    ended_at=parse_dt(data.get("ended_at")),
                    summary=data.get("summary"),
                    metadata=data.get("metadata", {}),
                    tags=data.get("tags", []),
                    memory_ids=data.get("memory_ids", []),
                    parent_episode_id=data.get("parent_episode_id")
                )
        return None

    async def close_episode(self, episode_id: str, summary: Optional[str] = None) -> None:
        """Close an active episode."""
        query = """
        UPDATE type::thing('episode', $id) SET
            status = 'closed',
            ended_at = time::now(),
            summary = $summary;
        """
        params = {
            "id": episode_id,
            "summary": summary
        }

        async with self.db_client.get_connection() as conn:
            await conn.query(query, params)

        logger.info(f"Closed episode {episode_id}")

    async def add_memory_to_episode(self, episode_id: str, memory_id: str) -> None:
        """Link a memory to an episode."""
        # 1. Update Episode's memory_ids list
        # 2. Update Memory's episode_id field

        # We can do this in a transaction or just two queries
        # SurrealDB supports transactions but for simplicity/speed let's use individual updates
        # actually, let's try to be consistent

        query = """
        BEGIN TRANSACTION;

        -- Add memory to episode list if not exists
        UPDATE type::thing('episode', $episode_id) SET memory_ids = array::union(memory_ids, [$memory_id]);

        -- Set episode_id on memory
        UPDATE type::thing('memory', $memory_id) SET episode_id = $episode_id;

        COMMIT TRANSACTION;
        """

        params = {
            "episode_id": episode_id,
            "memory_id": memory_id
        }

        async with self.db_client.get_connection() as conn:
            await conn.query(query, params)

        logger.info(f"Added memory {memory_id} to episode {episode_id}")

    async def get_active_episode(self, user_id: str) -> Optional[Episode]:
        """Get the most recent open episode for a user."""
        query = """
        SELECT * FROM episode
        WHERE user_id = $user_id AND status = 'open'
        ORDER BY started_at DESC
        LIMIT 1;
        """

        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, {"user_id": user_id})

            if response and isinstance(response, list):
                data = response[0]
                if isinstance(data, dict) and 'result' in data:
                     if data['result']:
                         data = data['result'][0]
                     else:
                         return None

                # Reuse parsing logic (duplication, should refactor if complex)
                def parse_dt(dt_val: Any) -> datetime:
                    if not dt_val: return None
                    if isinstance(dt_val, str):
                        if dt_val.endswith('Z'): dt_val = dt_val[:-1]
                        return datetime.fromisoformat(dt_val).replace(tzinfo=timezone.utc)
                    return dt_val

                ep_id = data.get("id")
                if isinstance(ep_id, str) and ep_id.startswith("episode:"):
                    ep_id = ep_id.split(":", 1)[1]

                return Episode(
                    id=ep_id,
                    user_id=data["user_id"],
                    title=data["title"],
                    description=data.get("description"),
                    status=EpisodeStatus(data["status"]),
                    started_at=parse_dt(data["started_at"]) or datetime.now(timezone.utc),
                    ended_at=parse_dt(data.get("ended_at")),
                    summary=data.get("summary"),
                    metadata=data.get("metadata", {}),
                    tags=data.get("tags", []),
                    memory_ids=data.get("memory_ids", []),
                    parent_episode_id=data.get("parent_episode_id")
                )
        return None

    async def get_episode_memories(self, episode_id: str) -> List[Memory]:
        """Retrieve all memories for a given episode."""
        query = """
        SELECT * FROM memory WHERE episode_id = $episode_id ORDER BY created_at ASC;
        """

        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, {"episode_id": episode_id})

            if response and isinstance(response, list):
                 # Handle possible wrapper
                items = response
                if isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']

                return [self.db_client._deserialize_memory(item) for item in items]
        return []
