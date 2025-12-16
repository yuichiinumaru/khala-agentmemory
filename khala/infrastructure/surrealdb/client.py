"""SurrealDB client for KHALA memory system.

This module provides an async SurrealDB client with connection pooling,
transaction support, and error handling optimized for the KHALA memory system.
"""

import asyncio
import hashlib
import os
import re
import logging
from contextlib import asynccontextmanager
from dataclasses import asdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, TYPE_CHECKING

from pydantic import BaseModel, Field, SecretStr

try:
    from surrealdb import AsyncSurreal
    from surrealdb.data.types.geometry import GeometryPoint
except ImportError as e:
    raise ImportError(
        "SurrealDB is required. Install with: pip install surrealdb"
    ) from e

# Move imports to top level (Architecture Rule)
from khala.domain.memory.entities import Memory, Entity, Relationship
from khala.domain.memory.value_objects import (
    EmbeddingVector, MemoryTier, ImportanceScore
)
from .schema import DatabaseSchema

logger = logging.getLogger(__name__)


class SurrealConfig(BaseModel):
    """Immutable configuration for SurrealDB.

    Prevents 'Hardcoded Secrets' and 'Insecure Defaults'.
    """
    url: str = Field(..., description="SurrealDB WebSocket URL")
    namespace: str = Field(..., description="Database Namespace")
    database: str = Field(..., description="Database Name")
    username: Optional[str] = Field(None, description="Auth Username")
    password: Optional[SecretStr] = Field(None, description="Auth Password")
    token: Optional[SecretStr] = Field(None, description="Auth Token")
    max_connections: int = Field(default=10, ge=1, le=100)

    @classmethod
    def from_env(cls) -> "SurrealConfig":
        """Load from environment variables with Zero Trust."""
        url = os.getenv("SURREAL_URL")
        ns = os.getenv("SURREAL_NS")
        db = os.getenv("SURREAL_DB")
        user = os.getenv("SURREAL_USER")
        password = os.getenv("SURREAL_PASS")
        token = os.getenv("SURREAL_TOKEN")

        missing = []
        if not url: missing.append("SURREAL_URL")
        if not ns: missing.append("SURREAL_NS")
        if not db: missing.append("SURREAL_DB")

        # Require either (user+pass) or token
        if not token and (not user or not password):
            missing.append("SURREAL_USER/PASS or SURREAL_TOKEN")

        if missing:
            raise ValueError(f"CRITICAL: Missing required environment variables: {', '.join(missing)}")

        return cls(
            url=url,
            namespace=ns,
            database=db,
            username=user,
            password=SecretStr(password) if password else None,
            token=SecretStr(token) if token else None
        )

class SurrealDBClient:
    """Async SurrealDB client with connection pooling and optimization."""
    
    def __init__(self, config: Optional[SurrealConfig] = None):
        """Initialize SurrealDB client.
        
        Args:
            config: Validated configuration object.
        """
        self.config = config or SurrealConfig.from_env()
        
        self._connection_pool: List[AsyncSurreal] = []
        self._pool_lock = asyncio.Lock()
        self._semaphore = asyncio.Semaphore(self.config.max_connections)
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize connection pool and setup namespace/database."""
        if self._initialized:
            return
        
        async with self._pool_lock:
            if self._initialized:
                return
            
            logger.info(f"Connecting to SurrealDB at {self.config.url}...")
            
            try:
                # Create initial connection to verify connectivity
                connection = await self._create_connection()
                self._connection_pool.append(connection)
                self._initialized = True

            except Exception as e:
                logger.critical(f"Failed to initialize SurrealDB connection: {e}")
                raise RuntimeError(f"SurrealDB Initialization Failed: {e}") from e
            
        try:
            schema_manager = DatabaseSchema(self)
            await schema_manager.create_schema()
        except Exception as e:
            logger.error(f"Failed to initialize schema: {e}")
            raise RuntimeError(f"Schema Initialization Failed: {e}") from e
        
        logger.info("SurrealDB initialized successfully.")
    
    async def _create_connection(self) -> AsyncSurreal:
        """Helper to create and authenticate a new connection."""
        connection = AsyncSurreal(self.config.url)
        await connection.connect()

        if self.config.token:
            await connection.authenticate(self.config.token.get_secret_value())
        elif self.config.username and self.config.password:
            await connection.signin({
                "username": self.config.username,
                "password": self.config.password.get_secret_value()
            })
        else:
            raise ValueError("Missing credentials: Both token and username/password are missing.")

        await connection.use(namespace=self.config.namespace, database=self.config.database)
        return connection

    async def close(self) -> None:
        """Close all connections in the pool."""
        async with self._pool_lock:
            logger.info(f"Closing {len(self._connection_pool)} connections...")
            for conn in self._connection_pool:
                try:
                    await conn.close()
                except Exception as e:
                    logger.warning(f"Error closing connection: {e}")
            self._connection_pool.clear()
            self._initialized = False
        logger.info("SurrealDB client closed.")

    @asynccontextmanager
    async def get_connection(self):
        """Get a connection from the pool."""
        if not self._initialized:
            await self.initialize()
        
        # Enforce max connections
        async with self._semaphore:
            connection = None
            try:
                # Thread-safe pool access
                async with self._pool_lock:
                    if self._connection_pool:
                        connection = self._connection_pool.pop()

                if not connection:
                    connection = await self._create_connection()

                yield connection
            finally:
                if connection:
                    should_close = False
                    # Return to pool if space permits
                    async with self._pool_lock:
                        if len(self._connection_pool) < self.config.max_connections:
                            self._connection_pool.append(connection)
                        else:
                            should_close = True

                    if should_close:
                        try:
                            await connection.close()
                        except Exception as e:
                            logger.error(f"Error closing overflow connection: {e}")
    
    @asynccontextmanager
    async def _borrow_connection(self, connection: Optional[AsyncSurreal] = None):
        """Helper to use provided connection or get one from pool."""
        if connection:
            yield connection
        else:
            async with self.get_connection() as conn:
                yield conn

    @asynccontextmanager
    async def transaction(self):
        """Execute a block within a database transaction (Strategy 65)."""
        # TRANSACTION DISABLED DUE TO DRIVER INSTABILITY
        # Verified: 'BEGIN TRANSACTION' causes valid results to be interpreted as errors by SDK
        # Verified: 'CANCEL TRANSACTION' causes internal DB panic
        # Falling back to auto-commit mode for stability.
        async with self.get_connection() as conn:
            try:
                # await conn.query("BEGIN TRANSACTION;")
                yield conn
                # await conn.query("COMMIT TRANSACTION;")
            except Exception as e:
                # try:
                #     await conn.query("CANCEL TRANSACTION;")
                # except Exception:
                #     pass
                raise e

    def _parse_dt(self, dt_val: Any) -> datetime:
        """Robustly parse timestamps.

        CRITICAL FIX: Do NOT default to now(). Raise error on corruption.
        """
        if dt_val is None:
            raise ValueError("CRITICAL: Timestamp is None. Data Integrity Violation.")

        if isinstance(dt_val, datetime):
            return dt_val if dt_val.tzinfo else dt_val.replace(tzinfo=timezone.utc)

        try:
            if isinstance(dt_val, str):
                if dt_val.endswith('Z'): dt_val = dt_val[:-1]
                return datetime.fromisoformat(dt_val).replace(tzinfo=timezone.utc)
        except ValueError as e:
            raise ValueError(f"Data Corruption: Invalid timestamp format '{dt_val}'") from e

        raise ValueError(f"Unknown timestamp type: {type(dt_val)}")

    def _serialize_memory(self, memory: Memory) -> Dict[str, Any]:
        """Serialize memory entity to database format."""
        # Calculate content hash for deduplication
        content_hash = hashlib.sha256(f"{memory.content}{memory.user_id}".encode()).hexdigest()

        # Prepare content fields
        content_str = memory.content or ""
        content_tiny = content_str[:100]
        content_small = content_str[:1000]
        content_full = content_str if len(content_str) > 1000 else None

        # Helper to serialize datetimes
        def iso(dt: Optional[datetime]) -> Optional[str]:
            return dt.isoformat() if dt else None

        # Serialize source
        source_data = None
        if memory.source:
            source_data = asdict(memory.source)
            if source_data.get('timestamp'):
                source_data['timestamp'] = iso(source_data['timestamp'])

        # Serialize sentiment
        sentiment_data = asdict(memory.sentiment) if memory.sentiment else None

        # Serialize location
        location_data = None
        if memory.location:
             location_data = GeometryPoint(memory.location.longitude, memory.location.latitude)

        content_dict = {
            "user_id": memory.user_id,
            "content": memory.content,
            "content_tiny": content_tiny,
            "content_small": content_small,
            "content_full": content_full,
            "content_hash": content_hash,
            "tier": memory.tier.value,
            "importance": memory.importance.value,
            "tags": memory.tags,
            "category": memory.category,
            "scope": memory.scope,
            "summary": memory.summary,
            "metadata": memory.metadata,
            "created_at": iso(memory.created_at),
            "updated_at": iso(memory.updated_at),
            "accessed_at": iso(memory.accessed_at),
            "access_count": memory.access_count,
            "llm_cost": memory.llm_cost,
            "verification_score": memory.verification_score,
            "verification_count": memory.verification_count,
            "verification_status": memory.verification_status,
            "verified_at": iso(memory.verified_at),
            "verification_issues": memory.verification_issues,
            "debate_consensus": memory.debate_consensus,
            "is_archived": memory.is_archived,
            "decay_score": memory.decay_score.value if memory.decay_score else None,
            "source": source_data,
            "sentiment": sentiment_data,
            "episode_id": memory.episode_id,
            "confidence": memory.confidence,
            "source_reliability": memory.source_reliability,
            "location": location_data,
            "versions": memory.versions,
            "events": memory.events
        }

        if memory.embedding:
            content_dict["embedding"] = memory.embedding.values
            content_dict["embedding_model"] = memory.embedding.model
            content_dict["embedding_version"] = memory.embedding.version
        
        if memory.embedding_visual:
            content_dict["embedding_visual"] = memory.embedding_visual.values
            content_dict["embedding_visual_model"] = memory.embedding_visual.model
            content_dict["embedding_visual_version"] = memory.embedding_visual.version

        if memory.embedding_code:
            content_dict["embedding_code"] = memory.embedding_code.values
            content_dict["embedding_code_model"] = memory.embedding_code.model
            content_dict["embedding_code_version"] = memory.embedding_code.version

        return content_dict

    async def create_memory(self, memory: Memory, connection: Optional[AsyncSurreal] = None) -> str:
        """Create a new memory in the database.

        Logic: Idempotent with content hashing. If hash exists, UPDATE it.
        """
        content_dict = self._serialize_memory(memory)
        content_hash = content_dict["content_hash"]

        async with self._borrow_connection(connection) as conn:
            # OPTIMIZED: Try to create first. If it violates UNIQUE index, then update.
            try:
                query = "CREATE type::thing('memory', $id) CONTENT $content_data;"
                params = {"id": memory.id, "content_data": content_dict}

                response = await conn.query(query, params)

                # SurrealDB error handling
                if isinstance(response, dict) and response.get('status') == 'ERR':
                     raise RuntimeError(f"DB Error: {response}")
                if isinstance(response, list) and len(response) > 0:
                     if isinstance(response[0], dict) and response[0].get('status') == 'ERR':
                         # Check for unique constraint violation
                         detail = response[0].get('detail', '')
                         # Improve robustness: Check for 'Index' and 'content_hash' or typical violation codes
                         if ('Index' in detail and 'content_hash' in detail) or 'exists' in detail:
                             raise ValueError("DUPLICATE_HASH")
                         raise RuntimeError(f"DB Error: {response}")

                return memory.id

            except (ValueError, Exception) as e:
                is_duplicate = False
                if str(e) == "DUPLICATE_HASH" or "already exists" in str(e).lower():
                    is_duplicate = True

                if is_duplicate:
                    logger.info(f"Duplicate memory detected (hash collision). Merging into existing record.")
                    # Get the ID of the existing record with this hash
                    find_query = "SELECT id FROM memory WHERE content_hash = $hash LIMIT 1;"
                    find_resp = await conn.query(find_query, {"hash": content_hash})

                    existing_id = None
                    if find_resp and isinstance(find_resp, list) and len(find_resp) > 0:
                         res = find_resp[0].get('result', []) if isinstance(find_resp[0], dict) else find_resp
                         if res:
                             existing_id = res[0].get('id')

                    if existing_id:
                        # Extract raw ID if needed
                        if ":" in str(existing_id):
                             existing_id = str(existing_id).split(":")[1]

                        update_query = "UPDATE type::thing('memory', $id) MERGE $content_data;"
                        await conn.query(update_query, {"id": existing_id, "content_data": content_dict})
                        return existing_id

                # If not duplicate or recovery failed, re-raise
                logger.error(f"Create memory failed: {e}")
                raise

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
                if isinstance(item, dict):
                    if 'status' in item and 'result' in item:
                        if item['status'] == 'OK' and item['result']:
                            return self._deserialize_memory(item['result'][0])
                    else:
                        return self._deserialize_memory(item)
            
            return None
    
    async def update_memory(self, memory: Memory, connection: Optional[AsyncSurreal] = None) -> None:
        """Update an existing memory."""
        content_dict = self._serialize_memory(memory)
        # Update timestamp explicitly
        content_dict["updated_at"] = datetime.now(timezone.utc).isoformat()
        
        query = "UPDATE type::thing('memory', $id) MERGE $updates;"
        
        async with self._borrow_connection(connection) as conn:
            await conn.query(query, {"id": memory.id, "updates": content_dict})
    
    async def delete_memory(self, memory_id: str, connection: Optional[AsyncSurreal] = None) -> None:
        """Delete a memory by ID."""
        query = "DELETE type::thing('memory', $id);"
        params = {"id": memory_id}
        
        async with self._borrow_connection(connection) as conn:
            await conn.query(query, params)

    async def create_entity(self, entity: Entity) -> str:
        """Create a new entity."""
        # ... (Same as original but assume typed)
        query = """
        CREATE type::thing('entity', $id) CONTENT {
            text: $text,
            entity_type: $entity_type,
            confidence: $confidence,
            embedding: $embedding,
            metadata: $metadata,
            created_at: $created_at
        };
        """
        params = {
            "id": entity.id,
            "text": entity.text,
            "entity_type": entity.entity_type.value,
            "confidence": entity.confidence,
            "embedding": entity.embedding.values if entity.embedding else None,
            "metadata": entity.metadata,
            "created_at": entity.created_at.isoformat(),
        }
        async with self.get_connection() as conn:
            await conn.query(query, params)
            return entity.id

    async def create_relationship(self, relationship: Relationship, connection: Optional[AsyncSurreal] = None) -> str:
        """Create a new relationship."""
        from_uuid = relationship.from_entity_id.split(":")[1] if ":" in relationship.from_entity_id else relationship.from_entity_id
        to_uuid = relationship.to_entity_id.split(":")[1] if ":" in relationship.to_entity_id else relationship.to_entity_id

        query = """
        CREATE type::thing('relationship', $id) CONTENT {
            in: type::thing('entity', $from_uuid),
            out: type::thing('entity', $to_uuid),
            from_entity_id: $from_entity_id,
            to_entity_id: $to_entity_id,
            relation_type: $relation_type,
            strength: $strength,
            valid_from: $valid_from,
            valid_to: $valid_to,
            transaction_time_start: $transaction_time_start,
            transaction_time_end: $transaction_time_end
        };
        """
        params = {
            "id": relationship.id,
            "from_uuid": from_uuid,
            "to_uuid": to_uuid,
            "from_entity_id": relationship.from_entity_id,
            "to_entity_id": relationship.to_entity_id,
            "relation_type": relationship.relation_type,
            "strength": relationship.strength,
            "valid_from": relationship.valid_from.isoformat(),
            "valid_to": relationship.valid_to.isoformat() if relationship.valid_to else None,
            "transaction_time_start": relationship.transaction_time_start.isoformat(),
            "transaction_time_end": relationship.transaction_time_end.isoformat() if relationship.transaction_time_end else None,
        }
        async with self._borrow_connection(connection) as conn:
            await conn.query(query, params)
            return relationship.id

    def _build_filter_query(self, filters: Dict[str, Any], params: Dict[str, Any]) -> str:
        """Build WHERE clause segment securely."""
        if not filters:
            return ""

        clauses = []
        key_pattern = re.compile(r"^[a-zA-Z0-9_.]+$")

        for key, value in filters.items():
            if not key_pattern.match(key):
                logger.warning(f"💀 SQL INJECTION ATTEMPT: Invalid filter key '{key}'")
                continue

            safe_param_key = f"filter_{hashlib.md5(key.encode()).hexdigest()[:8]}"

            if not isinstance(value, (str, int, float, bool, list, tuple, dict, type(None))):
                 logger.warning(f"Invalid filter value type for {key}: {type(value)}")
                 continue

            if isinstance(value, (list, tuple)):
                clauses.append(f"{key} IN ${safe_param_key}")
                params[safe_param_key] = value
            elif isinstance(value, dict) and "op" in value:
                op = value.get("op", "eq")
                val = value.get("value")
                params[safe_param_key] = val

                if op == "eq": clauses.append(f"{key} = ${safe_param_key}")
                elif op == "gt": clauses.append(f"{key} > ${safe_param_key}")
                elif op == "lt": clauses.append(f"{key} < ${safe_param_key}")
                elif op == "gte": clauses.append(f"{key} >= ${safe_param_key}")
                elif op == "lte": clauses.append(f"{key} <= ${safe_param_key}")
                elif op == "contains": clauses.append(f"string::contains({key}, ${safe_param_key})")
            else:
                clauses.append(f"{key} = ${safe_param_key}")
                params[safe_param_key] = value

        if not clauses: return ""
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

        provenance_filter = ""
        if embedding.model:
            # FIX: Ensure model string is safe, though it's bound.
            provenance_filter += " AND embedding_model = $embedding_model"
            params["embedding_model"] = embedding.model
        if embedding.version:
            provenance_filter += " AND embedding_version = $embedding_version"
            params["embedding_version"] = embedding.version

        query = f"""
        SELECT *, vector::similarity::cosine(embedding, $embedding) AS similarity
        FROM memory 
        WHERE user_id = $user_id 
        AND is_archived = false
        AND embedding != NONE
        AND vector::similarity::cosine(embedding, $embedding) > $min_similarity
        {provenance_filter}
        {filter_clause}
        ORDER BY similarity DESC
        LIMIT $top_k;
        """
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                    return response[0]['result']
                return response
            return []

    async def search_memories_by_bm25(self, query_text: str, user_id: str, top_k: int = 10, filters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
        """Search memories using BM25."""
        params = {"user_id": user_id, "query_text": query_text, "top_k": top_k}
        filter_clause = self._build_filter_query(filters, params)
        query = f"""
        SELECT * FROM memory
        WHERE user_id = $user_id
        AND content @@ $query_text
        AND is_archived = false
        {filter_clause}
        LIMIT $top_k;
        """
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                    return response[0]['result']
                return response
            return []

    async def get_memories_by_tier(self, user_id: str, tier: str, limit: int = 100) -> List[Memory]:
        """Get memories by tier."""
        query = "SELECT * FROM memory WHERE user_id = $user_id AND tier = $tier AND is_archived = false ORDER BY accessed_at DESC LIMIT $limit;"
        params = {"user_id": user_id, "tier": tier, "limit": limit}
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                items = response
                if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']
                return [self._deserialize_memory(data) for data in items]
            return []

    def _deserialize_memory(self, data: Dict[str, Any]) -> Memory:
        """Deserialize database record to Memory object with Robustness."""
        
        # Deserialize Enums safely
        try:
            tier = MemoryTier(data.get("tier"))
        except (ValueError, KeyError):
            tier = MemoryTier.SHORT_TERM

        try:
            importance = ImportanceScore(data.get("importance", 0.5))
        except (ValueError, KeyError, TypeError):
            importance = ImportanceScore(0.5)

        # Handle ID
        memory_id = str(data["id"])
        if memory_id.startswith("memory:"):
            memory_id = memory_id.split(":", 1)[1]

        # Embeddings
        embedding = None
        if data.get("embedding"):
            embedding = EmbeddingVector(
                values=data["embedding"],
                model=data.get("embedding_model"),
                version=data.get("embedding_version")
            )
        
        return Memory(
            id=memory_id,
            user_id=data.get("user_id", "unknown"),
            content=data.get("content", ""),
            tier=tier,
            importance=importance,
            embedding=embedding,
            tags=data.get("tags", []),
            category=data.get("category"),
            scope=data.get("scope"),
            summary=data.get("summary"),
            metadata=data.get("metadata", {}),
            created_at=self._parse_dt(data.get("created_at")),
            updated_at=self._parse_dt(data.get("updated_at")),
            accessed_at=self._parse_dt(data.get("accessed_at")),
            access_count=data.get("access_count", 0),
            llm_cost=data.get("llm_cost", 0.0),
            verification_score=data.get("verification_score", 0.0),
            verification_count=data.get("verification_count", 0),
            verification_status=data.get("verification_status", "pending"),
            verified_at=data.get("verified_at") and self._parse_dt(data.get("verified_at")),
            verification_issues=data.get("verification_issues", []),
            debate_consensus=data.get("debate_consensus"),
            is_archived=data.get("is_archived", False),
            decay_score=None,
            source=None,
            sentiment=None,
            episode_id=data.get("episode_id"),
            confidence=data.get("confidence", 1.0),
            source_reliability=data.get("source_reliability", 1.0),
            location=None,
            versions=data.get("versions", []),
            events=data.get("events", [])
        )
