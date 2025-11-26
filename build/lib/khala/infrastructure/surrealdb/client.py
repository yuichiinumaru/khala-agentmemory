"""SurrealDB client for KHALA memory system.

This module provides an async SurrealDB client with connection pooling,
transaction support, and error handling optimized for the KHALA memory system.
"""

import asyncio
from typing import Dict, List, Optional, Any, Union
import logging
from contextlib import asynccontextmanager

try:
    from surrealdb import Surreal, AsyncSurreal
except ImportError as e:
    raise ImportError(
        "SurrealDB is required. Install with: pip install surrealdb"
    ) from e

from khala.domain.memory.entities import Memory, Entity, Relationship
from khala.domain.memory.value_objects import EmbeddingVector

logger = logging.getLogger(__name__)


class SurrealDBClient:
    """Async SurrealDB client with connection pooling and optimization."""
    
    def __init__(
        self,
        url: str = "ws://localhost:8000/rpc",
        namespace: str = "khala",
        database: str = "memories",
        username: str = "root",
        password: str = "root",
        max_connections: int = 10,
    ):
        """Initialize SurrealDB client.
        
        Args:
            url: WebSocket URL for SurrealDB
            namespace: Namespace to use (multi-tenancy)
            database: Database to use
            username: Authentication username
            password: Authentication password
            max_connections: Maximum connections in pool
        """
        self.url = url
        self.namespace = namespace
        self.database = database
        self.username = username
        self.password = password
        self.max_connections = max_connections
        
        self._connection_pool: List[AsyncSurreal] = []
        self._pool_lock = asyncio.Lock()
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize connection pool and setup namespace/database."""
        if self._initialized:
            return
        
        async with self._pool_lock:
            if self._initialized:
                return
            
            # Create initial connection
            connection = AsyncSurreal(self.url)
            await connection.connect()
            await connection.signin({"username": self.username, "password": self.password})
            
            # Define namespace and database if they don't exist
            try:
                await connection.query(f"DEFINE NAMESPACE {self.namespace};")
            except Exception as e:
                logger.debug(f"Namespace {self.namespace} might already exist: {e}")
            
            await connection.use(namespace=self.namespace, database=self.database)
            
            # Add to pool
            self._connection_pool.append(connection)
            self._initialized = True
            
            logger.info(f"Connected to SurrealDB at {self.url}")
    
    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        if not self._initialized:
            await self.initialize()
        
        connection = None
        try:
            if self._connection_pool:
                connection = self._connection_pool.pop()
            else:
                # Create new connection if pool is empty
                connection = AsyncSurreal(self.url)
                await connection.connect()
                await connection.signin({"username": self.username, "password": self.password})
                await connection.use(namespace=self.namespace, database=self.database)
            
            yield connection
        finally:
            if connection:
                # Return connection to pool if not full
                if len(self._connection_pool) < self.max_connections:
                    self._connection_pool.append(connection)
                else:
                    # Close connection if pool is full
                    try:
                        await connection.close()
                    except Exception as e:
                        logger.error(f"Error closing connection: {e}")
    
    async def create_memory(self, memory: Memory) -> str:
        """Create a new memory in the database."""
        query = """
        CREATE memory CONTENT {
            id: $id,
            user_id: $user_id,
            content: $content,
            embedding: $embedding,
            tier: $tier,
            importance: $importance,
            tags: $tags,
            category: $category,
            metadata: $metadata,
            created_at: $created_at,
            updated_at: $updated_at,
            accessed_at: $accessed_at,
            access_count: $access_count,
            llm_cost: $llm_cost,
            verification_score: $verification_score,
            verification_issues: $verification_issues,
            debate_consensus: $debate_consensus,
            is_archived: $is_archived,
            decay_score: $decay_score
        };
        """
        
        params = {
            "id": memory.id,
            "user_id": memory.user_id,
            "content": memory.content,
            "embedding": memory.embedding.values if memory.embedding else None,
            "tier": memory.tier.value,
            "importance": memory.importance.value,
            "tags": memory.tags,
            "category": memory.category,
            "metadata": memory.metadata,
            "created_at": memory.created_at.isoformat(),
            "updated_at": memory.updated_at.isoformat(),
            "accessed_at": memory.accessed_at.isoformat(),
            "access_count": memory.access_count,
            "llm_cost": memory.llm_cost,
            "verification_score": memory.verification_score,
            "verification_issues": memory.verification_issues,
            "debate_consensus": memory.debate_consensus,
            "is_archived": memory.is_archived,
            "decay_score": memory.decay_score.value if memory.decay_score else None,
        }
        
        async with self.get_connection() as conn:
            result = await conn.query(query, params)
            return memory.id
    
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID."""
        query = "SELECT * FROM memory WHERE id = $id;"
        params = {"id": memory_id}
        
        async with self.get_connection() as conn:
            result = await conn.query(query, params)
            
            if not result:
                return None
            
            # Parse result and create Memory object
            data = result[0]
            return self._deserialize_memory(data)
    
    async def update_memory(self, memory: Memory) -> None:
        """Update an existing memory."""
        query = """
        UPDATE $id CONTENT {
            user_id: $user_id,
            content: $content,
            embedding: $embedding,
            tier: $tier,
            importance: $importance,
            tags: $tags,
            category: $category,
            metadata: $metadata,
            updated_at: time::now(),
            accessed_at: $accessed_at,
            access_count: $access_count,
            llm_cost: $llm_cost,
            verification_score: $verification_score,
            verification_issues: $verification_issues,
            debate_consensus: $debate_consensus,
            is_archived: $is_archived,
            decay_score: $decay_score
        } WHERE id = $id;
        """
        
        params = {
            "id": memory.id,
            "user_id": memory.user_id,
            "content": memory.content,
            "embedding": memory.embedding.values if memory.embedding else None,
            "tier": memory.tier.value,
            "importance": memory.importance.value,
            "tags": memory.tags,
            "category": memory.category,
            "metadata": memory.metadata,
            "accessed_at": memory.accessed_at.isoformat(),
            "access_count": memory.access_count,
            "llm_cost": memory.llm_cost,
            "verification_score": memory.verification_score,
            "verification_issues": memory.verification_issues,
            "debate_consensus": memory.debate_consensus,
            "is_archived": memory.is_archived,
            "decay_score": memory.decay_score.value if memory.decay_score else None,
        }
        
        async with self.get_connection() as conn:
            await conn.query(query, params)
    
    async def delete_memory(self, memory_id: str) -> None:
        """Delete a memory by ID."""
        query = "DELETE FROM memory WHERE id = $id;"
        params = {"id": memory_id}
        
        async with self.get_connection() as conn:
            await conn.query(query, params)
    
    async def search_memories_by_vector(
        self, 
        embedding: EmbeddingVector, 
        user_id: str,
        top_k: int = 10,
        min_similarity: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Search memories using vector similarity."""
        query = """
        SELECT * 
        FROM memory 
        WHERE user_id = $user_id 
          AND embedding <|1, $min_similarity|> $embedding
          AND is_archived = false
        LIMIT $top_k;
        """
        
        params = {
            "user_id": user_id,
            "embedding": embedding.values,
            "min_similarity": min_similarity,
            "top_k": top_k,
        }
        
        async with self.get_connection() as conn:
            result = await conn.query(query, params)
            return result if result else []
    
    async def search_memories_by_bm25(
        self,
        query_text: str,
        user_id: str,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """Search memories using BM25 full-text search."""
        query = """
        SELECT *
        FROM memory
        WHERE user_id = $user_id
          AND content @@ $query_text
          AND is_archived = false
        LIMIT $top_k;
        """
        
        params = {
            "user_id": user_id,
            "query_text": query_text,
            "top_k": top_k,
        }
        
        async with self.get_connection() as conn:
            result = await conn.query(query, params)
            return result if result else []
    
    async def get_memories_by_tier(
        self,
        user_id: str,
        tier: str,
        limit: int = 100
    ) -> List[Memory]:
        """Get memories by tier for a user."""
        query = """
        SELECT *
        FROM memory
        WHERE user_id = $user_id
          AND tier = $tier
          AND is_archived = false
        ORDER BY accessed_at DESC
        LIMIT $limit;
        """
        
        params = {
            "user_id": user_id,
            "tier": tier,
            "limit": limit,
        }
        
        async with self.get_connection() as conn:
            result = await conn.query(query, params)
            return [self._deserialize_memory(data) for data in result] if result else []
    
    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self._pool_lock:
            for connection in self._connection_pool:
                try:
                    await connection.close()
                except Exception as e:
                    logger.error(f"Error closing connection: {e}")
            self._connection_pool.clear()
            self._initialized = False
    
    def _deserialize_memory(self, data: Dict[str, Any]) -> Memory:
        """Deserialize database record to Memory object."""
        # Convert timestamp strings back to datetime objects
        from datetime import datetime, timezone
        
        def parse_dt(dt_str: str) -> datetime:
            if dt_str:
                # Remove timezone info if present and add UTC
                if dt_str.endswith('Z'):
                    dt_str = dt_str[:-1]
                return datetime.fromisoformat(dt_str).replace(tzinfo=timezone.utc)
            return datetime.now(timezone.utc)
        
        # Convert embedding back to EmbeddingVector
        embedding = None
        if data.get("embedding"):
            embedding = EmbeddingVector(data["embedding"])
        
        # Create Memory object
        from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
        
        return Memory(
            id=data["id"],
            user_id=data["user_id"],
            content=data["content"],
            tier=MemoryTier(data["tier"]),
            importance=ImportanceScore(data["importance"]),
            embedding=embedding,
            tags=data.get("tags", []),
            category=data.get("category"),
            metadata=data.get("metadata", {}),
            created_at=parse_dt(data["created_at"]),
            updated_at=parse_dt(data["updated_at"]),
            accessed_at=parse_dt(data["accessed_at"]),
            access_count=data.get("access_count", 0),
            llm_cost=data.get("llm_cost", 0.0),
            verification_score=data.get("verification_score", 0.0),
            verification_issues=data.get("verification_issues", []),
            debate_consensus=data.get("debate_consensus"),
            is_archived=data.get("is_archived", False),
            decay_score=None,  # Would need to recreate DecayScore if needed
        )
