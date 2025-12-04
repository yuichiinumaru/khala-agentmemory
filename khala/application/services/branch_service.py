"""Branch Service for Version Control (Module 15).

This service implements Strategies 156 (Version Control) and 157 (Forking Capabilities).
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
import uuid
import copy

from khala.domain.memory.entities import Memory
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class BranchService:
    """Service for managing memory branches and forks."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def create_branch(
        self,
        name: str,
        user_id: str,
        parent_branch_id: Optional[str] = None
    ) -> str:
        """Create a new branch."""
        branch_data = {
            "name": name,
            "user_id": user_id, # stored as created_by
            "created_by": user_id,
            "parent_branch_id": parent_branch_id,
            "status": "active",
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }

        async with self.db_client.get_connection() as conn:
            # SurrealDB create returns list of records
            result = await conn.create("branch", branch_data)

            if isinstance(result, list) and len(result) > 0:
                return result[0]['id']
            elif isinstance(result, dict) and 'id' in result:
                return result['id']

            # If creating via query for table:
            # But conn.create usually works.
            # Fallback if result format varies
            logger.warning(f"Unexpected result from create branch: {result}")
            # Try to return ID if nested
            return "branch:unknown"

    async def fork_memory(self, memory_id: str, target_branch_id: str) -> str:
        """
        Fork a memory into a target branch (Strategy 157).

        Implements Copy-on-Write semantics by creating a new memory record
        linked to the original via `fork_parent_id`.
        """
        # Handle full ID vs short ID
        if "memory:" in memory_id:
            memory_id = memory_id.split("memory:")[1]

        original = await self.db_client.get_memory(memory_id)
        if not original:
            raise ValueError(f"Memory {memory_id} not found")

        # Create copy
        fork_id = str(uuid.uuid4())

        # New memory properties
        new_memory = copy.deepcopy(original)
        new_memory.id = fork_id
        new_memory.branch_id = target_branch_id
        new_memory.fork_parent_id = memory_id
        new_memory.created_at = datetime.now(timezone.utc)
        new_memory.updated_at = datetime.now(timezone.utc)

        # Reset specific fields
        new_memory.versions = []
        new_memory.access_count = 0
        new_memory.verification_score = 0.0

        # Metadata
        new_memory.metadata["forked_from"] = memory_id
        new_memory.metadata["forked_at"] = datetime.now(timezone.utc).isoformat()

        await self.db_client.create_memory(new_memory)

        return fork_id

    async def get_branch_memories(self, branch_id: str, limit: int = 100) -> List[Memory]:
        """Get all memories associated with a branch."""
        query = "SELECT * FROM memory WHERE branch_id = $bid LIMIT $limit;"
        params = {"bid": branch_id, "limit": limit}

        async with self.db_client.get_connection() as conn:
            result = await conn.query(query, params)

            items = []
            # Handle SurrealDB response format
            if isinstance(result, list) and len(result) > 0:
                if isinstance(result[0], dict) and 'result' in result[0]:
                    items = result[0]['result']
                else:
                    items = result

            memories = []
            for item in items:
                try:
                    # Accessing protected method from client to reuse deserialization logic
                    mem = self.db_client._deserialize_memory(item)
                    memories.append(mem)
                except Exception as e:
                    logger.warning(f"Failed to deserialize memory {item.get('id')}: {e}")

            return memories
