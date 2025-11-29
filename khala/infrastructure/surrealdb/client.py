"""SurrealDB client for KHALA memory system.

This module provides an async SurrealDB client with connection pooling,
transaction support, and error handling optimized for the KHALA memory system.
"""

import asyncio
import hashlib
from typing import Dict, List, Optional, Any, Union
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict

try:
    from surrealdb import Surreal, AsyncSurreal
except ImportError as e:
    raise ImportError(
        "SurrealDB is required. Install with: pip install surrealdb"
    ) from e

from khala.domain.memory.entities import Memory, Entity, Relationship
from khala.domain.memory.value_objects import EmbeddingVector, MemorySource, Sentiment
from khala.domain.skills.entities import Skill
from khala.domain.skills.value_objects import SkillType, SkillLanguage, SkillParameter
from .schema import DatabaseSchema

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
            
            # Initialize Schema using DatabaseSchema manager
            try:
                schema_manager = DatabaseSchema(self)
                await schema_manager.create_schema()
            except Exception as e:
                logger.error(f"Failed to initialize schema: {e}")
            
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
        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(f"{memory.content}{memory.user_id}".encode()).hexdigest()

        query = """
        CREATE type::thing('memory', $id) CONTENT {
            user_id: $user_id,
            content: $content,
            content_hash: $content_hash,
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
            verification_count: $verification_count,
            verification_status: $verification_status,
            verified_at: $verified_at,
            verification_issues: $verification_issues,
            debate_consensus: $debate_consensus,
            is_archived: $is_archived,
            decay_score: $decay_score,
            source: $source,
            sentiment: $sentiment
        };
        """
        
        # Serialize source and handle datetime
        source_data = None
        if memory.source:
            source_data = asdict(memory.source)
            if source_data.get('timestamp'):
                source_data['timestamp'] = source_data['timestamp'].isoformat()

        # Serialize sentiment
        sentiment_data = None
        if memory.sentiment:
            sentiment_data = asdict(memory.sentiment)

        params = {
            "id": memory.id,
            "user_id": memory.user_id,
            "content": memory.content,
            "content_hash": content_hash,
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
            "verification_count": memory.verification_count,
            "verification_status": memory.verification_status,
            "verified_at": memory.verified_at.isoformat() if memory.verified_at else None,
            "verification_issues": memory.verification_issues,
            "debate_consensus": memory.debate_consensus,
            "is_archived": memory.is_archived,
            "decay_score": memory.decay_score.value if memory.decay_score else None,
            "source": source_data,
            "sentiment": sentiment_data,
        }
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            
            # Check for error string
            if isinstance(response, str):
                 logger.error(f"Create memory failed: {response}")
                 raise RuntimeError(f"Failed to create memory: {response}")
            
            # Check for list of results
            if isinstance(response, list):
                if not response:
                    logger.error("Create memory returned empty list")
                    raise RuntimeError("Failed to create memory: empty response")
                
                # If it's a list of dicts, it's likely the created record(s)
                # Check if it looks like an error object (if Surreal returns dict errors)
                if isinstance(response[0], dict):
                    if response[0].get('status') == 'ERR':
                        logger.error(f"Create memory failed: {response}")
                        raise RuntimeError(f"Failed to create memory: {response}")
            
            return memory.id
    
    async def get_memory(self, memory_id: str) -> Optional[Memory]:
        """Get a memory by ID."""
        query = "SELECT * FROM type::thing('memory', $id);"
        params = {"id": memory_id}
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            
            if not response:
                return None
            
            if isinstance(response, list) and len(response) > 0:
                item = response[0]
                # If item is the record itself
                if isinstance(item, dict):
                    # Check if it's a status object or the record
                    if 'status' in item and 'result' in item:
                        if item['status'] == 'OK' and item['result']:
                            return self._deserialize_memory(item['result'][0])
                    else:
                        # Assume it's the record
                        return self._deserialize_memory(item)
            
            return None
    
    async def update_memory(self, memory: Memory) -> None:
        """Update an existing memory."""
        # Recalculate hash on update
        content_hash = hashlib.sha256(f"{memory.content}{memory.user_id}".encode()).hexdigest()

        query = """
        UPDATE type::thing('memory', $id) CONTENT {
            user_id: $user_id,
            content: $content,
            content_hash: $content_hash,
            embedding: $embedding,
            tier: $tier,
            importance: $importance,
            tags: $tags,
            category: $category,
            metadata: $metadata,
            created_at: $created_at,
            updated_at: time::now(),
            accessed_at: $accessed_at,
            access_count: $access_count,
            llm_cost: $llm_cost,
            verification_score: $verification_score,
            verification_count: $verification_count,
            verification_status: $verification_status,
            verified_at: $verified_at,
            verification_issues: $verification_issues,
            debate_consensus: $debate_consensus,
            is_archived: $is_archived,
            decay_score: $decay_score,
            source: $source,
            sentiment: $sentiment
        };
        """
        
        # Serialize source and handle datetime
        source_data = None
        if memory.source:
            source_data = asdict(memory.source)
            if source_data.get('timestamp'):
                source_data['timestamp'] = source_data['timestamp'].isoformat()

        # Serialize sentiment
        sentiment_data = None
        if memory.sentiment:
            sentiment_data = asdict(memory.sentiment)

        params = {
            "id": memory.id,
            "user_id": memory.user_id,
            "content": memory.content,
            "content_hash": content_hash,
            "embedding": memory.embedding.values if memory.embedding else None,
            "tier": memory.tier.value,
            "importance": memory.importance.value,
            "tags": memory.tags,
            "category": memory.category,
            "metadata": memory.metadata,
            "created_at": memory.created_at.isoformat(),
            "accessed_at": memory.accessed_at.isoformat(),
            "access_count": memory.access_count,
            "llm_cost": memory.llm_cost,
            "verification_score": memory.verification_score,
            "verification_count": memory.verification_count,
            "verification_status": memory.verification_status,
            "verified_at": memory.verified_at.isoformat() if memory.verified_at else None,
            "verification_issues": memory.verification_issues,
            "debate_consensus": memory.debate_consensus,
            "is_archived": memory.is_archived,
            "decay_score": memory.decay_score.value if memory.decay_score else None,
            "source": source_data,
            "sentiment": sentiment_data,
        }
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if isinstance(response, str):
                 raise RuntimeError(f"Failed to update memory: {response}")
    
    async def delete_memory(self, memory_id: str) -> None:
        """Delete a memory by ID."""
        query = "DELETE type::thing('memory', $id);"
        params = {"id": memory_id}
        
        async with self.get_connection() as conn:
            await conn.query(query, params)

    def _build_filter_query(self, filters: Dict[str, Any], params: Dict[str, Any]) -> str:
        """Build WHERE clause segment from filters and update params."""
        if not filters:
            return ""

        clauses = []
        for key, value in filters.items():
            # Validate key (alphanumeric, underscore, dot)
            if not all(c.isalnum() or c in "_." for c in key):
                logger.warning(f"Skipping invalid filter key: {key}")
                continue

            safe_param_key = f"filter_{key.replace('.', '_')}"

            if isinstance(value, (list, tuple)):
                clauses.append(f"{key} IN ${safe_param_key}")
                params[safe_param_key] = value
            elif isinstance(value, dict) and "op" in value:
                op = value.get("op", "eq")
                val = value.get("value")
                params[safe_param_key] = val

                if op == "eq":
                    clauses.append(f"{key} = ${safe_param_key}")
                elif op == "gt":
                    clauses.append(f"{key} > ${safe_param_key}")
                elif op == "lt":
                    clauses.append(f"{key} < ${safe_param_key}")
                elif op == "gte":
                    clauses.append(f"{key} >= ${safe_param_key}")
                elif op == "lte":
                    clauses.append(f"{key} <= ${safe_param_key}")
                elif op == "contains":
                    clauses.append(f"string::contains({key}, ${safe_param_key})")
            else:
                clauses.append(f"{key} = ${safe_param_key}")
                params[safe_param_key] = value

        if not clauses:
            return ""

        return " AND " + " AND ".join(clauses)
    
    async def search_memories_by_vector(
        self, 
        embedding: EmbeddingVector, 
        user_id: str,
        top_k: int = 10,
        min_similarity: float = 0.6,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search memories using vector similarity."""
        params = {
            "user_id": user_id,
            "embedding": embedding.values,
            "min_similarity": min_similarity,
            "top_k": top_k,
        }

        filter_clause = self._build_filter_query(filters, params)

        query = f"""
        SELECT *, vector::similarity::cosine(embedding, $embedding) AS similarity
        FROM memory 
        WHERE user_id = $user_id 
        AND is_archived = false
        AND embedding != NONE
        AND vector::similarity::cosine(embedding, $embedding) > $min_similarity
        {filter_clause}
        ORDER BY similarity DESC
        LIMIT $top_k;
        """
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                # If list of dicts, return it
                return response
            return []
    
    async def search_memories_by_bm25(
        self,
        query_text: str,
        user_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search memories using BM25 full-text search."""
        params = {
            "user_id": user_id,
            "query_text": query_text,
            "top_k": top_k,
        }

        filter_clause = self._build_filter_query(filters, params)

        query = f"""
        SELECT *
        FROM memory
        WHERE user_id = $user_id
        AND content @@ $query_text
        AND is_archived = false
        {filter_clause}
        LIMIT $top_k;
        """
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                return response
            return []
    
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
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                return [self._deserialize_memory(data) for data in response]
            return []
    
    async def listen_live(self, table: str) -> Any:
        """
        Subscribe to changes on a table using LIVE SELECT.
        Yields events as they happen.
        """
        async with self.get_connection() as conn:
            try:
                # 1. Start the LIVE query to get the UUID
                if hasattr(conn, "live"):
                    query_uuid = await conn.live(table)
                    logger.info(f"Started LIVE query on {table} with UUID: {query_uuid}")
                    
                    # 2. Subscribe to the live query using the UUID
                    if hasattr(conn, "subscribe_live"):
                        stream = await conn.subscribe_live(query_uuid)
                        async for event in stream:
                            yield event
                    else:
                        logger.warning("SurrealDB client missing subscribe_live method.")
                        yield {"error": "subscribe_live not found"}
                else:
                    logger.warning("SurrealDB client does not support live() method.")
                    yield {"error": "live() not supported"}
                    
            except Exception as e:
                logger.error(f"Error in LIVE query: {e}")
                raise

    async def kill_live(self, query_uuid: str) -> None:
        """Kill a running LIVE query."""
        async with self.get_connection() as conn:
            if hasattr(conn, "kill"):
                await conn.kill(query_uuid)
            else:
                # Fallback to raw query if kill method missing
                await conn.query("KILL $uuid;", {"uuid": query_uuid})
            logger.info(f"Killed LIVE query: {query_uuid}")
    
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
        
        def parse_dt(dt_val: Any) -> datetime:
            if not dt_val:
                return datetime.now(timezone.utc)
            
            if isinstance(dt_val, datetime):
                # Ensure timezone awareness
                if dt_val.tzinfo is None:
                    return dt_val.replace(tzinfo=timezone.utc)
                return dt_val
                
            if isinstance(dt_val, str):
                # Remove timezone info if present and add UTC
                if dt_val.endswith('Z'):
                    dt_val = dt_val[:-1]
                return datetime.fromisoformat(dt_val).replace(tzinfo=timezone.utc)
            
            return datetime.now(timezone.utc)
        
        # Convert embedding back to EmbeddingVector
        embedding = None
        if data.get("embedding"):
            embedding = EmbeddingVector(data["embedding"])
        
        # Reconstruct MemorySource
        source = None
        if data.get("source"):
            src_data = data["source"]
            if src_data.get("timestamp"):
                src_data["timestamp"] = parse_dt(src_data["timestamp"])
            try:
                source = MemorySource(**src_data)
            except Exception as e:
                logger.warning(f"Failed to deserialize MemorySource: {e}")

        # Reconstruct Sentiment
        sentiment = None
        if data.get("sentiment"):
            try:
                sentiment = Sentiment(**data["sentiment"])
            except Exception as e:
                logger.warning(f"Failed to deserialize Sentiment: {e}")

        # Create Memory object
        from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
        
        # Handle ID: if it contains 'memory:', strip it for the entity ID
        memory_id = data["id"]
        if isinstance(memory_id, str) and memory_id.startswith("memory:"):
            memory_id = memory_id.split(":", 1)[1]
        
        return Memory(
            id=memory_id,
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
            verification_count=data.get("verification_count", 0),
            verification_status=data.get("verification_status", "pending"),
            verified_at=parse_dt(data.get("verified_at")),
            verification_issues=data.get("verification_issues", []),
            debate_consensus=data.get("debate_consensus"),
            is_archived=data.get("is_archived", False),
            decay_score=None,  # Would need to recreate DecayScore if needed
            source=source,
            sentiment=sentiment
        )

    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve past search sessions for a user."""
        query = """
        SELECT * FROM search_session
        WHERE user_id = $user_id
        ORDER BY created_at DESC
        LIMIT $limit;
        """
        params = {"user_id": user_id, "limit": limit}
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                return response
            return []

    async def create_skill(self, skill: Skill) -> str:
        """Create a new skill in the database."""
        query = """
        CREATE type::thing('skill', $id) CONTENT {
            name: $name,
            description: $description,
            code: $code,
            language: $language,
            skill_type: $skill_type,
            parameters: $parameters,
            return_type: $return_type,
            dependencies: $dependencies,
            tags: $tags,
            metadata: $metadata,
            embedding: $embedding,
            created_at: $created_at,
            updated_at: $updated_at,
            version: $version,
            is_active: $is_active
        };
        """
        
        # Serialize parameters
        serialized_params = [
            {
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "required": p.required,
                "default_value": p.default_value
            }
            for p in skill.parameters
        ]
        
        params = {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "code": skill.code,
            "language": skill.language.value,
            "skill_type": skill.skill_type.value,
            "parameters": serialized_params,
            "return_type": skill.return_type,
            "dependencies": skill.dependencies,
            "tags": skill.tags,
            "metadata": skill.metadata,
            "embedding": skill.embedding.values if skill.embedding else None,
            "created_at": skill.created_at.isoformat(),
            "updated_at": skill.updated_at.isoformat(),
            "version": skill.version,
            "is_active": skill.is_active
        }
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if isinstance(response, str):
                 raise RuntimeError(f"Failed to create skill: {response}")
            return skill.id

    async def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID."""
        query = "SELECT * FROM type::thing('skill', $id);"
        params = {"id": skill_id}
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            
            if not response:
                return None
            
            if isinstance(response, list) and len(response) > 0:
                item = response[0]
                if isinstance(item, dict):
                    if 'status' in item and 'result' in item:
                        if item['status'] == 'OK' and item['result']:
                            return self._deserialize_skill(item['result'][0])
                    else:
                        return self._deserialize_skill(item)
            
            return None

    async def update_skill(self, skill: Skill) -> None:
        """Update an existing skill."""
        query = """
        UPDATE type::thing('skill', $id) CONTENT {
            name: $name,
            description: $description,
            code: $code,
            language: $language,
            skill_type: $skill_type,
            parameters: $parameters,
            return_type: $return_type,
            dependencies: $dependencies,
            tags: $tags,
            metadata: $metadata,
            embedding: $embedding,
            created_at: $created_at,
            updated_at: time::now(),
            version: $version,
            is_active: $is_active
        };
        """
        
        serialized_params = [
            {
                "name": p.name,
                "type": p.type,
                "description": p.description,
                "required": p.required,
                "default_value": p.default_value
            }
            for p in skill.parameters
        ]
        
        params = {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "code": skill.code,
            "language": skill.language.value,
            "skill_type": skill.skill_type.value,
            "parameters": serialized_params,
            "return_type": skill.return_type,
            "dependencies": skill.dependencies,
            "tags": skill.tags,
            "metadata": skill.metadata,
            "embedding": skill.embedding.values if skill.embedding else None,
            "created_at": skill.created_at.isoformat(),
            "version": skill.version,
            "is_active": skill.is_active
        }
        
        async with self.get_connection() as conn:
            await conn.query(query, params)

    async def delete_skill(self, skill_id: str) -> None:
        """Delete a skill by ID."""
        query = "DELETE type::thing('skill', $id);"
        params = {"id": skill_id}
        
        async with self.get_connection() as conn:
            await conn.query(query, params)

    async def search_skills_by_vector(
        self, 
        embedding: EmbeddingVector, 
        top_k: int = 5,
        min_similarity: float = 0.6
    ) -> List[Dict[str, Any]]:
        """Search skills using vector similarity."""
        query = """
        SELECT *, vector::similarity::cosine(embedding, $embedding) AS similarity
        FROM skill 
        WHERE is_active = true
        AND embedding != NONE
        AND vector::similarity::cosine(embedding, $embedding) > $min_similarity
        ORDER BY similarity DESC
        LIMIT $top_k;
        """
        
        params = {
            "embedding": embedding.values,
            "min_similarity": min_similarity,
            "top_k": top_k,
        }
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                return response
            return []

    async def search_skills_by_text(
        self,
        query_text: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search skills using BM25 full-text search."""
        query = """
        SELECT *
        FROM skill
        WHERE description @@ $query_text
        OR name @@ $query_text
        AND is_active = true
        LIMIT $top_k;
        """
        
        params = {
            "query_text": query_text,
            "top_k": top_k,
        }
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                return response
            return []

    def _deserialize_skill(self, data: Dict[str, Any]) -> Skill:
        """Deserialize database record to Skill object."""
        from datetime import datetime, timezone
        
        def parse_dt(dt_val: Any) -> datetime:
            if not dt_val:
                return datetime.now(timezone.utc)
            if isinstance(dt_val, str):
                if dt_val.endswith('Z'):
                    dt_val = dt_val[:-1]
                return datetime.fromisoformat(dt_val).replace(tzinfo=timezone.utc)
            return dt_val

        # Handle ID
        skill_id = str(data["id"])
        if skill_id.startswith("skill:"):
            skill_id = skill_id.split(":", 1)[1]
            
        # Deserialize parameters
        parameters = []
        for p in data.get("parameters", []):
            parameters.append(SkillParameter(
                name=p["name"],
                type=p["type"],
                description=p["description"],
                required=p.get("required", True),
                default_value=p.get("default_value")
            ))
            
        # Embedding
        embedding = None
        if data.get("embedding"):
            embedding = EmbeddingVector(data["embedding"])

        return Skill(
            id=skill_id,
            name=data["name"],
            description=data["description"],
            code=data["code"],
            language=SkillLanguage(data["language"]),
            skill_type=SkillType(data["skill_type"]),
            parameters=parameters,
            return_type=data.get("return_type", "Any"),
            dependencies=data.get("dependencies", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            embedding=embedding,
            created_at=parse_dt(data["created_at"]),
            updated_at=parse_dt(data["updated_at"]),
            version=data.get("version", "1.0.0"),
            is_active=data.get("is_active", True)
        )
