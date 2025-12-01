from typing import List, Optional, Dict, Any
import logging

from khala.domain.memory.repository import MemoryRepository
from khala.domain.memory.entities import Memory, Branch
from khala.domain.memory.value_objects import EmbeddingVector
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.persistence.audit_repository import AuditRepository
from khala.domain.audit.entities import AuditLog

logger = logging.getLogger(__name__)

class SurrealDBMemoryRepository(MemoryRepository):
    """
    SurrealDB implementation of the MemoryRepository interface with Audit Logging.
    """
    
    def __init__(self, client: SurrealDBClient, audit_repo: Optional[AuditRepository] = None):
        self.client = client
        self.audit_repo = audit_repo or AuditRepository(client)
        
    async def create(self, memory: Memory) -> str:
        """Save a new memory."""
        memory_id = await self.client.create_memory(memory)
        await self.audit_repo.log(AuditLog(
            user_id=memory.user_id,
            action="create",
            target_id=memory_id,
            target_type="memory",
            details={"tier": memory.tier.value}
        ))
        return memory_id
        
    async def save(self, memory: Memory) -> str:
        """Save a memory (create or update)."""
        # This is a bit of a hack since create_memory handles upsert in some clients,
        # but let's assume we can determine if it exists or just use upsert logic.
        # In SurrealDB, CREATE fails if ID exists, UPDATE fails if ID doesn't exist.
        # UPSERT or LET $id = ...; UPDATE $id ... works.
        # client.update_memory usually handles existing IDs.

        # Check if memory exists, or try update and fallback to create.
        try:
            existing = await self.get_by_id(memory.id)
            if existing:
                await self.update(memory)
                return memory.id
            else:
                return await self.create(memory)
        except Exception as e:
            logger.error(f"Error saving memory: {e}")
            raise

    async def get_by_id(self, memory_id: str) -> Optional[Memory]:
        """Retrieve a memory by its ID."""
        # Auditing reads might be too verbose, but can be enabled if strict audit is required.
        # For now, we only audit state changes.
        return await self.client.get_memory(memory_id)
        
    async def update(self, memory: Memory) -> None:
        """Update an existing memory."""
        await self.client.update_memory(memory)
        await self.audit_repo.log(AuditLog(
            user_id=memory.user_id,
            action="update",
            target_id=memory.id,
            target_type="memory",
            details={"tier": memory.tier.value}
        ))
        
    async def delete(self, memory_id: str) -> None:
        """Delete a memory."""
        # We need to fetch the memory first to get user_id for audit
        memory = await self.get_by_id(memory_id)
        user_id = memory.user_id if memory else "unknown"

        await self.client.delete_memory(memory_id)
        await self.audit_repo.log(AuditLog(
            user_id=user_id,
            action="delete",
            target_id=memory_id,
            target_type="memory",
            details={}
        ))
        
    async def search_by_vector(
        self, 
        embedding: EmbeddingVector, 
        user_id: str, 
        top_k: int = 10, 
        min_similarity: float = 0.6,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Memory]:
        """Search memories by vector similarity."""
        results = await self.client.search_memories_by_vector(
            embedding=embedding,
            user_id=user_id,
            top_k=top_k,
            min_similarity=min_similarity,
            filters=filters
        )
        return [self.client._deserialize_memory(data) for data in results]
        
    async def search_by_text(
        self, 
        query_text: str, 
        user_id: str, 
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Memory]:
        """Search memories by text (BM25/Full-text)."""
        results = await self.client.search_memories_by_bm25(
            query_text=query_text,
            user_id=user_id,
            top_k=top_k,
            filters=filters
        )
        return [self.client._deserialize_memory(data) for data in results]
        
    async def get_by_tier(
        self, 
        user_id: str, 
        tier: str, 
        limit: int = 100
    ) -> List[Memory]:
        """Retrieve memories by tier."""
        return await self.client.get_memories_by_tier(
            user_id=user_id,
            tier=tier,
            limit=limit
        )

    async def save_branch(self, branch: Branch) -> str:
        """Save a branch entity."""
        # Convert branch entity to dictionary for SurrealDB
        data = {
            "id": branch.id,
            "name": branch.name,
            "parent": branch.parent_id,
            "description": branch.description,
            "created_at": branch.created_at.isoformat(),
            "created_by": branch.created_by
        }

        # Use direct query execution via client since there isn't a create_branch method in client yet
        # Or ideally, we should add create_branch to the client.
        # For now, using direct query.

        query = """
        UPDATE type::thing('branch', $id) CONTENT $data;
        """
        params = {"id": branch.id, "data": data}

        async with self.client.get_connection() as conn:
            await conn.query(query, params)

        return branch.id

    async def get_branch_by_id(self, branch_id: str) -> Optional[Branch]:
        """Retrieve a branch by ID."""
        query = "SELECT * FROM branch WHERE id = $id;"
        params = {"id": f"branch:{branch_id}" if not branch_id.startswith("branch:") else branch_id}

        async with self.client.get_connection() as conn:
            result = await conn.query(query, params)
            if result and result[0]["result"]:
                data = result[0]["result"][0]
                return self._deserialize_branch(data)
        return None

    async def get_branch_by_name(self, name: str) -> Optional[Branch]:
        """Retrieve a branch by name."""
        query = "SELECT * FROM branch WHERE name = $name;"
        params = {"name": name}

        async with self.client.get_connection() as conn:
            result = await conn.query(query, params)
            if result and result[0]["result"]:
                data = result[0]["result"][0]
                return self._deserialize_branch(data)
        return None

    def _deserialize_branch(self, data: Dict[str, Any]) -> Branch:
        """Convert DB result to Branch entity."""
        from datetime import datetime

        # Handle ID format "branch:xyz"
        branch_id = data["id"].split(":")[-1] if ":" in data["id"] else data["id"]

        return Branch(
            id=branch_id,
            name=data["name"],
            parent_id=data.get("parent"),
            description=data.get("description", ""),
            created_by=data.get("created_by", ""),
            # created_at might need parsing
            # Assuming client returns ISO string or datetime
            # If it's a string, parse it.
        )
    async def get_memory_facets(self, user_id: str) -> Dict[str, Any]:
        """Get faceted counts for memories."""
        return await self.client.get_memory_facets(user_id)
