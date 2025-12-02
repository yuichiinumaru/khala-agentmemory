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
    from surrealdb import Surreal
except ImportError as e:
    raise ImportError(
        "SurrealDB is required. Install with: pip install surrealdb"
    ) from e

from khala.domain.memory.entities import Memory, Entity, Relationship
from khala.domain.memory.value_objects import EmbeddingVector, MemorySource, Sentiment, GeoLocation
from khala.domain.memory.clustering import VectorCentroid
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
        
        self._connection_pool: List[Surreal] = []
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
            connection = Surreal(self.url)
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
                connection = Surreal(self.url)
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

        # Check for existing memory with same hash
        check_query = "SELECT id FROM memory WHERE content_hash = $content_hash LIMIT 1;"
        async with self.get_connection() as conn:
            check_response = await conn.query(check_query, {"content_hash": content_hash})
            
            # Handle SurrealDB response format
            items = []
            if check_response and isinstance(check_response, list):
                if len(check_response) > 0:
                    if isinstance(check_response[0], dict) and 'result' in check_response[0]:
                        items = check_response[0]['result']
                    else:
                        items = check_response

            if items and len(items) > 0:
                 existing_item = items[0]
                 existing_id = existing_item.get('id')
                 if existing_id:
                     existing_id = str(existing_id)
                     if existing_id.startswith("memory:"):
                         existing_id = existing_id.split(":")[1]
                     logger.info(f"Duplicate memory detected (hash collision). Returning existing ID: {existing_id}")
                     return existing_id

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
            sentiment: $sentiment,
            episode_id: $episode_id,
            agent_id: $agent_id,
            confidence: $confidence,
            source_reliability: $source_reliability,
            geo_location: $geo_location,
            location: $location
            project_id: $project_id,
            tenant_id: $tenant_id,
            summary_level: $summary_level,
            parent_summary_id: $parent_summary_id,
            child_memory_ids: $child_memory_ids
            branch: $branch,
            parent_memory: $parent_memory,
            version: $version
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

        # Serialize geo_location
        geo_location_data = None
        location_data = memory.location or {} # Preserve existing location data if any
        if memory.geo_location:
            geo_location_data = memory.geo_location.to_geojson()
            # Merge geo_location details into location_data, preserving existing keys
            # This ensures we don't overwrite user-defined location metadata
            geo_details = asdict(memory.geo_location)
            # Add/overwrite only the geospatial fields
            location_data.update(geo_details)

        params = {
            "id": memory.id,
            "user_id": memory.user_id,
            "content": memory.content,
            "content_hash": content_hash,
            "embedding": memory.embedding.values if memory.embedding else None,
            "embedding_visual": memory.embedding_visual.values if memory.embedding_visual else None,
            "embedding_code": memory.embedding_code.values if memory.embedding_code else None,
            "embedding_secondary": memory.embedding_secondary.values if memory.embedding_secondary else None,
            "embedding_small": memory.embedding_small.values if memory.embedding_small else None,
            "cluster_id": memory.cluster_id,
            "tier": memory.tier.value,
            "importance": memory.importance.value,
            "tags": memory.tags,
            "category": memory.category,
            "summary": memory.summary,
            "metadata": memory.metadata,
            "created_at": memory.created_at,
            "updated_at": memory.updated_at,
            "accessed_at": memory.accessed_at,
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
            "episode_id": memory.episode_id,
            "agent_id": memory.agent_id,
            "confidence": memory.confidence,
            "source_reliability": memory.source_reliability,
            "geo_location": geo_location_data,
            "location": location_data
            "project_id": memory.project_id,
            "tenant_id": memory.tenant_id,
            "summary_level": memory.summary_level,
            "parent_summary_id": memory.parent_summary_id,
            "child_memory_ids": memory.child_memory_ids,
            "branch": f"branch:{memory.branch_id}" if memory.branch_id else None,
            "parent_memory": f"memory:{memory.parent_memory_id}" if memory.parent_memory_id else None,
            "version": memory.version,
            "complexity": memory.complexity,
            "pos_tags": memory.pos_tags,
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
            embedding_secondary: $embedding_secondary,
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
            sentiment: $sentiment,
            episode_id: $episode_id,
            agent_id: $agent_id,
            confidence: $confidence,
            source_reliability: $source_reliability,
            geo_location: $geo_location,
            location: $location
            project_id: $project_id,
            tenant_id: $tenant_id,
            summary_level: $summary_level,
            parent_summary_id: $parent_summary_id,
            child_memory_ids: $child_memory_ids
            branch: $branch,
            parent_memory: $parent_memory,
            version: $version
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

        # Serialize geo_location
        geo_location_data = None
        location_data = memory.location or {}
        if memory.geo_location:
            geo_location_data = memory.geo_location.to_geojson()
            # Merge details
            geo_details = asdict(memory.geo_location)
            location_data.update(geo_details)

        params = {
            "id": memory.id,
            "user_id": memory.user_id,
            "content": memory.content,
            "content_hash": content_hash,
            "embedding": memory.embedding.values if memory.embedding else None,
            "embedding_secondary": memory.embedding_secondary.values if memory.embedding_secondary else None,
            "embedding_small": memory.embedding_small.values if memory.embedding_small else None,
            "cluster_id": memory.cluster_id,
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
            "episode_id": memory.episode_id,
            "agent_id": memory.agent_id,
            "confidence": memory.confidence,
            "source_reliability": memory.source_reliability,
            "geo_location": geo_location_data,
            "location": location_data
            "project_id": memory.project_id,
            "tenant_id": memory.tenant_id,
            "summary_level": memory.summary_level,
            "parent_summary_id": memory.parent_summary_id,
            "child_memory_ids": memory.child_memory_ids,
            "branch": f"branch:{memory.branch_id}" if memory.branch_id else None,
            "parent_memory": f"memory:{memory.parent_memory_id}" if memory.parent_memory_id else None,
            "version": memory.version,
            "complexity": memory.complexity,
            "pos_tags": memory.pos_tags,
        }
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if isinstance(response, str):
                 raise RuntimeError(f"Failed to update memory: {response}")

    async def update_memory_transactional(
        self,
        memory: Memory,
        updates: Dict[str, Any],
        event: Dict[str, Any]
    ) -> None:
        """Update memory with history and events atomically (Task 65).

        Wraps update, history appending, and event logging in a single transaction.

        Args:
            memory: The memory object to update.
            updates: Dictionary of fields to update.
            event: Event object to append to the events list.
        """
        # Prepare updates
        set_clauses = []

        # Handle ID prefix
        memory_id = memory.id
        if ":" in memory_id:
            memory_id = memory_id.split(":")[1]

        params = {"id": memory_id, "event": event}

        # Serialize updates and build SET clauses
        for key, value in updates.items():
            if key == "metadata":
                # Merge metadata instead of replacing
                set_clauses.append(f"metadata = metadata || ${key}")
                params[key] = value
            else:
                set_clauses.append(f"{key} = ${key}")
                params[key] = value

        # Always update updated_at
        set_clauses.append("updated_at = time::now()")

        # Build the transactional query
        # 1. Capture current version for history (Strategy 60: Document Versioning)
        #    Use [0] to get the object from the list result
        # 2. Update the fields
        # 3. Append to events (Strategy 61: Array-Based Accumulation)
        query = f"""
        BEGIN TRANSACTION;

        LET $current_doc = (SELECT * FROM type::thing('memory', $id))[0];

        UPDATE type::thing('memory', $id) SET
            {', '.join(set_clauses)},
            versions = array::append(versions ?? [], {{
                timestamp: time::now(),
                diff: $current_doc
            }}),
            events = array::append(events ?? [], $event);

        COMMIT TRANSACTION;
        """

        async with self.get_connection() as conn:
            response = await conn.query(query, params)

            # Check for errors in transaction
            if isinstance(response, list):
                for item in response:
                    if isinstance(item, dict) and item.get('status') == 'ERR':
                        logger.error(f"Transaction failed: {item}")
                        raise RuntimeError(f"Transaction failed: {item.get('detail')}")
    
    async def delete_memory(self, memory_id: str) -> None:
        """Delete a memory by ID."""
        query = "DELETE type::thing('memory', $id);"
        params = {"id": memory_id}
        
        async with self.get_connection() as conn:
            await conn.query(query, params)

    async def create_entity(self, entity: Entity) -> str:
        """Create a new entity in the database."""
        query = """
        CREATE type::thing('entity', $id) CONTENT {
            text: $text,
            entity_type: $entity_type,
            confidence: $confidence,
            embedding: $embedding,
            metadata: $metadata,
            created_at: $created_at,
            last_seen: $last_seen
        };
        """

        params = {
            "id": entity.id,
            "text": entity.text,
            "entity_type": entity.entity_type.value,
            "confidence": entity.confidence,
            "embedding": entity.embedding.values if entity.embedding else None,
            "metadata": entity.metadata,
            "created_at": entity.created_at,
            "last_seen": entity.last_seen,
        }

        async with self.get_connection() as conn:
            await conn.query(query, params)
            return entity.id

    async def update_entity_last_seen(self, entity_id: str, last_seen: Any = None) -> None:
        """Update the last_seen timestamp of an entity."""
        if ":" in entity_id:
            entity_id = entity_id.split(":")[1]

        if last_seen is None:
            query = "UPDATE type::thing('entity', $id) SET last_seen = time::now();"
            params = {"id": entity_id}
        else:
            query = "UPDATE type::thing('entity', $id) SET last_seen = $last_seen;"
            params = {"id": entity_id, "last_seen": last_seen}

        async with self.get_connection() as conn:
            await conn.query(query, params)

    async def get_entity_by_text_and_type(self, text: str, entity_type: str) -> Optional[Entity]:
        """Get an entity by text and type (unique constraint)."""
        query = """
        SELECT * FROM entity
        WHERE text = $text
        AND entity_type = $entity_type
        LIMIT 1;
        """
        params = {"text": text, "entity_type": entity_type}

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list) and len(response) > 0:
                item = response[0]
                if isinstance(item, dict):
                    if 'status' in item and 'result' in item:
                        if item['status'] == 'OK' and item['result']:
                            return self._deserialize_entity(item['result'][0])
                    else:
                        return self._deserialize_entity(item)
            return None

    def _deserialize_entity(self, data: Dict[str, Any]) -> Entity:
        """Deserialize database record to Entity object."""
        from datetime import datetime, timezone
        from khala.domain.memory.entities import EntityType

        def parse_dt(dt_val: Any) -> datetime:
            if not dt_val: return datetime.now(timezone.utc)
            if isinstance(dt_val, str):
                if dt_val.endswith('Z'): dt_val = dt_val[:-1]
                return datetime.fromisoformat(dt_val).replace(tzinfo=timezone.utc)
            return dt_val

        entity_id = str(data["id"])
        if entity_id.startswith("entity:"):
            entity_id = entity_id.split(":", 1)[1]

        embedding = None
        if data.get("embedding"):
            embedding = EmbeddingVector(data["embedding"])

        entity = Entity(
            id=entity_id,
            text=data["text"],
            entity_type=EntityType(data["entity_type"]),
            confidence=data.get("confidence", 1.0),
            embedding=embedding,
            metadata=data.get("metadata", {}),
            created_at=parse_dt(data.get("created_at"))
        )
        if data.get("last_seen"):
            entity.last_seen = parse_dt(data.get("last_seen"))

        return entity

    async def create_relationship(self, relationship: Relationship) -> str:
        """Create a new relationship in the database."""
    async def create_relationship(self, relationship: Relationship, bidirectional: bool = False) -> str:
        """Create a new relationship in the database.

        Args:
            relationship: The relationship entity to create.
            bidirectional: If True, automatically creates the inverse edge.
        """
        # Parse entity IDs to extract UUIDs if they are in record format
        from_uuid = relationship.from_entity_id
        if ":" in from_uuid:
            from_uuid = from_uuid.split(":")[1]
            
        to_uuid = relationship.to_entity_id
        if ":" in to_uuid:
            to_uuid = to_uuid.split(":")[1]

        query = """
        CREATE type::thing('relationship', $id) CONTENT {
            in: type::thing('entity', $from_uuid),
            out: type::thing('entity', $to_uuid),
            from_entity_id: $from_entity_id,
            to_entity_id: $to_entity_id,
            relation_type: $relation_type,
            strength: $strength,
            weight: $weight,
            valid_from: $valid_from,
            valid_to: $valid_to,
            transaction_time_start: $transaction_time_start,
            transaction_time_end: $transaction_time_end,
            agent_id: $agent_id,
            is_consensus: $is_consensus,
            consensus_data: $consensus_data,
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
            "weight": relationship.weight,
            "valid_from": relationship.valid_from,
            "valid_to": relationship.valid_to,
            "transaction_time_start": relationship.transaction_time_start,
            "transaction_time_end": relationship.transaction_time_end,
            "agent_id": relationship.agent_id,
            "is_consensus": relationship.is_consensus,
            "consensus_data": relationship.consensus_data,
        }

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            
            # Check for errors
            if isinstance(response, list) and len(response) > 0:
                if isinstance(response[0], dict) and 'status' in response[0] and response[0]['status'] == 'ERR':
                    logger.error(f"Create relationship failed: {response[0]}")
                    raise RuntimeError(f"Failed to create relationship: {response[0].get('detail', 'Unknown error')}")

            # Handle bidirectional creation
            if bidirectional:
                # Create the inverse relationship
                inverse_query = """
                CREATE type::thing('relationship', $inverse_id) CONTENT {
                    in: type::thing('entity', $to_uuid),
                    out: type::thing('entity', $from_uuid),
                    from_entity_id: $to_entity_id,
                    to_entity_id: $from_entity_id,
                    relation_type: $relation_type,
                    strength: $strength,
                    valid_from: $valid_from,
                    valid_to: $valid_to,
                    transaction_time_start: $transaction_time_start,
                    transaction_time_end: $transaction_time_end,
                    metadata: {
                        is_inverse: true,
                        original_relationship_id: $original_id
                    }
                };
                """

                # Generate a new ID for the inverse relationship
                import uuid
                inverse_id = str(uuid.uuid4())

                inverse_params = {
                    "inverse_id": inverse_id,
                    "original_id": relationship.id,
                    "from_uuid": from_uuid,
                    "to_uuid": to_uuid,
                    "from_entity_id": relationship.from_entity_id,
                    "to_entity_id": relationship.to_entity_id,
                    "relation_type": relationship.relation_type,
                    "strength": relationship.strength,
                    "valid_from": relationship.valid_from,
                    "valid_to": relationship.valid_to,
                    "transaction_time_start": relationship.transaction_time_start,
                    "transaction_time_end": relationship.transaction_time_end,
                }

                await conn.query(inverse_query, inverse_params)
                    
            return relationship.id

    async def update_relationship_validity(
        self,
        relationship_id: str,
        valid_from: Optional[Any] = None,
        valid_to: Optional[Any] = None
    ) -> None:
        """Update the validity period of a relationship (Bi-temporal correction)."""
        if ":" in relationship_id:
            relationship_id = relationship_id.split(":")[1]

        updates = []
        params = {"id": relationship_id}

        if valid_from:
            updates.append("valid_from = $valid_from")
            params["valid_from"] = valid_from

        if valid_to:
            updates.append("valid_to = $valid_to")
            params["valid_to"] = valid_to

        if not updates:
            return

        query = f"UPDATE type::thing('relationship', $id) SET {', '.join(updates)};"

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
        filters: Optional[Dict[str, Any]] = None,
        field_name: str = "embedding"
    ) -> List[Dict[str, Any]]:
        """Search memories using vector similarity.

        Args:
            field_name: The embedding field to search (embedding, embedding_secondary, etc)
        """
        # Sanitize field name to prevent injection
        allowed_fields = ["embedding", "embedding_secondary", "embedding_visual", "embedding_code"]
        if field_name not in allowed_fields:
            raise ValueError(f"Invalid embedding field name: {field_name}")

        params = {
            "user_id": user_id,
            "embedding": embedding.values,
            "min_similarity": min_similarity,
            "top_k": top_k,
        }

        filter_clause = self._build_filter_query(filters, params)

        query = f"""
        SELECT *, vector::similarity::cosine({field_name}, $embedding) AS similarity
        FROM memory 
        WHERE user_id = $user_id 
        AND is_archived = false
        AND {field_name} != NONE
        AND vector::similarity::cosine({field_name}, $embedding) > $min_similarity
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
    
    async def search_memories_by_location(
        self,
        location: Dict[str, float],
        radius_km: float,
        user_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search memories by geospatial location."""
        # Convert lat/lon to GeoJSON point
        point = {
            "type": "Point",
            "coordinates": [location["lon"], location["lat"]]
        }

        params = {
            "user_id": user_id,
            "point": point,
            "radius_m": radius_km * 1000.0,
            "top_k": top_k
        }

        filter_clause = self._build_filter_query(filters, params)

        query = f"""
        SELECT *, geo::distance(location, $point) AS distance
        FROM memory
        WHERE user_id = $user_id
        AND location IS NOT NONE
        AND geo::distance(location, $point) < $radius_m
        {filter_clause}
        ORDER BY distance ASC
        LIMIT $top_k;
        """

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                    return response[0]['result']
                return response
            return []

    async def get_graph_snapshot(
        self,
        user_id: Optional[str] = None
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Fetch all entities and relationships."""
        entity_query = "SELECT * FROM entity;"
        rel_query = "SELECT * FROM relationship WHERE valid_to IS NONE OR valid_to > time::now();"

        async with self.get_connection() as conn:
            entities_resp = await conn.query(entity_query)
            rels_resp = await conn.query(rel_query)

            entities = []
            if entities_resp and isinstance(entities_resp, list):
                 if len(entities_resp) > 0 and isinstance(entities_resp[0], dict) and 'result' in entities_resp[0]:
                     entities = entities_resp[0]['result']
                 else:
                     entities = entities_resp

            rels = []
            if rels_resp and isinstance(rels_resp, list):
                 if len(rels_resp) > 0 and isinstance(rels_resp[0], dict) and 'result' in rels_resp[0]:
                     rels = rels_resp[0]['result']
                 else:
                     rels = rels_resp

            return {"entities": entities, "relationships": rels}

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

    async def get_relationships(
        self,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 1000
    ) -> List[Dict[str, Any]]:
        """Get relationships with filtering."""
        params = {"limit": limit}
        # Pre-process filters if values are lists (for IN clause)
        # _build_filter_query handles list as IN, but key must match field.

        filter_clause = self._build_filter_query(filters, params)
        if filter_clause:
             filter_clause = "AND " + filter_clause.replace(" AND ", "", 1) if filter_clause.startswith(" AND ") else "AND " + filter_clause

        query = f"""
        SELECT * FROM relationship
        WHERE 1=1 {filter_clause}
    async def get_latest_memories(
        self,
        user_id: str,
        limit: int = 100
    ) -> List[Memory]:
        """Get latest memories for a user regardless of tier."""
        query = """
        SELECT *
        FROM memory
        WHERE user_id = $user_id
        AND is_archived = false
        AND embedding != NONE
        ORDER BY created_at DESC
        LIMIT $limit;
        """

        params = {
            "user_id": user_id,
            "limit": limit,
        }

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                return [self._deserialize_memory(data) for data in response]
            return []

    async def find_outliers_by_centroid(
        self,
        centroid: List[float],
        user_id: str,
        limit: int = 10,
        max_similarity: float = 0.5
    ) -> List[Dict[str, Any]]:
        """Find memories that are least similar to the centroid vector."""
        params = {
            "user_id": user_id,
            "centroid": centroid,
            "max_similarity": max_similarity,
            "limit": limit,
        }

        query = """
        SELECT *, vector::similarity::cosine(embedding, $centroid) AS similarity
        FROM memory
        WHERE user_id = $user_id
        AND is_archived = false
        AND embedding != NONE
        AND vector::similarity::cosine(embedding, $centroid) < $max_similarity
        ORDER BY similarity ASC
        LIMIT $limit;
        """

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     if response[0]['status'] == 'OK':
                        return response[0]['result']
                # If raw list of dicts (typical for select)
                return response
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

    async def get_memory_creation_stats(
        self,
        start_time: "datetime",
        end_time: "datetime",
        granularity: str = "day"
    ) -> List[Dict[str, Any]]:
        """Get memory creation statistics for heatmaps.

        Strategy 140: Temporal Heatmaps.

        Args:
            start_time: Start of the period
            end_time: End of the period
            granularity: 'hour', 'day', 'week'
        """
        duration_map = {
            "hour": "1h",
            "day": "1d",
            "week": "1w"
        }
        duration = duration_map.get(granularity, "1d")

        query = """
        SELECT count() AS count, time::floor(created_at, $duration) AS time_bucket
        FROM memory
        WHERE created_at >= $start AND created_at <= $end
        GROUP BY time_bucket
        ORDER BY time_bucket ASC;
        """

        params = {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "duration": duration
        }

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                 if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     return response[0]['result']
                 return response
            return []

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
        
        embedding_visual = None
        if data.get("embedding_visual"):
            embedding_visual = EmbeddingVector(data["embedding_visual"])

        embedding_code = None
        if data.get("embedding_code"):
            embedding_code = EmbeddingVector(data["embedding_code"])

        embedding_secondary = None
        if data.get("embedding_secondary"):
            embedding_secondary = EmbeddingVector(data["embedding_secondary"])
        embedding_small = None
        if data.get("embedding_small"):
            embedding_small = EmbeddingVector(data["embedding_small"])

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

        # Reconstruct GeoLocation
        geo_location = None
        if data.get("location") and isinstance(data["location"], dict):
            # Try to reconstruct from 'location' field if it matches GeoLocation structure
            try:
                if "latitude" in data["location"] and "longitude" in data["location"]:
                    geo_location = GeoLocation(**data["location"])
            except Exception as e:
                logger.debug(f"Failed to deserialize GeoLocation from location field: {e}")

        if not geo_location and data.get("geo_location"):
            # Fallback to coordinates from geo_location if location field is missing/invalid
            try:
                coords = data["geo_location"]["coordinates"]
                geo_location = GeoLocation(latitude=coords[1], longitude=coords[0])
            except Exception as e:
                logger.warning(f"Failed to deserialize GeoLocation from geometry: {e}")

        # Create Memory object
        from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
        
        # Handle ID: if it contains 'memory:', strip it for the entity ID
        memory_id = str(data["id"])
        if memory_id.startswith("memory:"):
            memory_id = memory_id.split(":", 1)[1]
        
        return Memory(
            id=memory_id,
            user_id=data["user_id"],
            content=data["content"],
            tier=MemoryTier(data["tier"]),
            importance=ImportanceScore(data["importance"]),
            embedding=embedding,
            embedding_visual=embedding_visual,
            embedding_code=embedding_code,
            embedding_secondary=embedding_secondary,
            embedding_small=embedding_small,
            cluster_id=data.get("cluster_id"),
            tags=data.get("tags", []),
            category=data.get("category"),
            summary=data.get("summary"),
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
            sentiment=sentiment,
            episode_id=data.get("episode_id"),
            agent_id=data.get("agent_id"),
            confidence=data.get("confidence", 1.0),
            source_reliability=data.get("source_reliability", 1.0),
            geo_location=geo_location,
            location=data.get("location")
            location=data.get("location")
        )

    def _deserialize_entity(self, data: Dict[str, Any]) -> Entity:
        """Deserialize database record to Entity object."""
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
        entity_id = str(data["id"])
        if entity_id.startswith("entity:"):
            entity_id = entity_id.split(":", 1)[1]

        embedding = None
        if data.get("embedding"):
            embedding = EmbeddingVector(data["embedding"])

        from khala.domain.memory.entities import Entity, EntityType

        return Entity(
            id=entity_id,
            text=data["text"],
            entity_type=EntityType(data["entity_type"]),
            confidence=data["confidence"],
            embedding=embedding,
            metadata=data.get("metadata", {}),
            created_at=parse_dt(data["created_at"])
        )

    def _deserialize_relationship(self, data: Dict[str, Any]) -> Relationship:
        """Deserialize database record to Relationship object."""
            project_id=data.get("project_id"),
            tenant_id=data.get("tenant_id"),
            summary_level=data.get("summary_level", 0),
            parent_summary_id=data.get("parent_summary_id"),
            child_memory_ids=data.get("child_memory_ids", [])
            branch_id=data.get("branch").split(":")[-1] if data.get("branch") and isinstance(data.get("branch"), str) and ":" in data.get("branch") else (data.get("branch") if isinstance(data.get("branch"), str) else None),
            parent_memory_id=data.get("parent_memory").split(":")[-1] if data.get("parent_memory") and isinstance(data.get("parent_memory"), str) and ":" in data.get("parent_memory") else (data.get("parent_memory") if isinstance(data.get("parent_memory"), str) else None),
            version=data.get("version", 1)
            complexity=data.get("complexity", 0.0)
            pos_tags=data.get("pos_tags")
        )

    async def save_centroid(self, centroid: VectorCentroid) -> str:
        """Save a vector centroid."""
        query = """
        CREATE type::thing('vector_centroid', $id) CONTENT {
            cluster_id: $cluster_id,
            embedding: $embedding,
            member_count: $member_count,
            radius: $radius,
            metadata: $metadata,
            created_at: $created_at,
            updated_at: $updated_at
        };
        """
        params = {
            "id": centroid.cluster_id,
            "cluster_id": centroid.cluster_id,
            "embedding": centroid.embedding.values,
            "member_count": centroid.member_count,
            "radius": centroid.radius,
            "metadata": centroid.metadata,
            "created_at": centroid.created_at.isoformat(),
            "updated_at": centroid.updated_at.isoformat(),
        }

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if isinstance(response, str):
                 raise RuntimeError(f"Failed to save centroid: {response}")
            return centroid.cluster_id

    async def get_all_centroids(self) -> List[VectorCentroid]:
        """Get all vector centroids."""
        query = "SELECT * FROM vector_centroid;"

        async with self.get_connection() as conn:
            response = await conn.query(query)
            if response and isinstance(response, list):
                return [self._deserialize_centroid(data) for data in response]
            return []

    async def update_memory_cluster(self, memory_id: str, cluster_id: str) -> None:
        """Efficiently update only the cluster_id of a memory."""
        # Handle memory ID format
        if memory_id.startswith("memory:"):
            memory_id = memory_id.split(":", 1)[1]

        query = "UPDATE type::thing('memory', $id) SET cluster_id = $cluster_id, updated_at = time::now();"
        params = {
            "id": memory_id,
            "cluster_id": cluster_id
        }

        async with self.get_connection() as conn:
            await conn.query(query, params)

    def _deserialize_centroid(self, data: Dict[str, Any]) -> VectorCentroid:
        """Deserialize database record to VectorCentroid object."""
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
        rel_id = str(data["id"])
        if rel_id.startswith("relationship:"):
            rel_id = rel_id.split(":", 1)[1]

        return Relationship(
            id=rel_id,
            from_entity_id=data["from_entity_id"],
            to_entity_id=data["to_entity_id"],
            relation_type=data["relation_type"],
            strength=data["strength"],
            valid_from=parse_dt(data["valid_from"]),
            valid_to=parse_dt(data.get("valid_to")),
            transaction_time_start=parse_dt(data["transaction_time_start"]),
            transaction_time_end=parse_dt(data.get("transaction_time_end"))
        embedding = None
        if data.get("embedding"):
            embedding = EmbeddingVector(data["embedding"])

        return VectorCentroid(
            embedding=embedding,
            cluster_id=data.get("cluster_id"),
            member_count=data.get("member_count", 0),
            radius=data.get("radius", 0.0),
            metadata=data.get("metadata", {}),
            created_at=parse_dt(data.get("created_at")),
            updated_at=parse_dt(data.get("updated_at"))
        )

    async def get_memory_facets(self, user_id: str) -> Dict[str, Any]:
        """Get faceted counts for memories."""
        query = """
        SELECT count() as count, tier FROM memory WHERE user_id = $user_id GROUP BY tier;
        SELECT count() as count, category FROM memory WHERE user_id = $user_id GROUP BY category;
        SELECT count() as count, metadata.agent_id as agent_id FROM memory WHERE user_id = $user_id GROUP BY metadata.agent_id;
        """

        async with self.get_connection() as conn:
            responses = await conn.query(query, {"user_id": user_id})

            facets = {
                "tier": {},
                "category": {},
                "agent_id": {}
            }

            # Helper to extract items from response list
            def extract_items(response_item):
                if isinstance(response_item, dict) and 'result' in response_item:
                    return response_item['result']
                if isinstance(response_item, list):
                    return response_item
                return []

            if responses and isinstance(responses, list):
                # Tier
                if len(responses) > 0:
                    for item in extract_items(responses[0]):
                        if 'tier' in item and item['tier']:
                             facets["tier"][str(item['tier'])] = item['count']

                # Category
                if len(responses) > 1:
                     for item in extract_items(responses[1]):
                        if 'category' in item and item['category']:
                             facets["category"][str(item['category'])] = item['count']

                # Agent
                if len(responses) > 2:
                     for item in extract_items(responses[2]):
                        val = item.get('agent_id') or item.get('metadata', {}).get('agent_id')
                        if val:
                             facets["agent_id"][str(val)] = item['count']

            return facets

    async def create_search_session(self, session_data: Dict[str, Any]) -> str:
        """Create a new search session log.

        Args:
            session_data: Dictionary containing session data (user_id, query, etc)

        Returns:
            The ID of the created session
        """
        query = """
        CREATE search_session CONTENT {
            user_id: $user_id,
            query: $query,
            expanded_queries: $expanded_queries,
            filters: $filters,
            timestamp: time::now(),
            results_count: $results_count,
            metadata: $metadata
        };
        """

        params = {
            "user_id": session_data.get("user_id"),
            "query": session_data.get("query"),
            "expanded_queries": session_data.get("expanded_queries", []),
            "filters": session_data.get("filters", {}),
            "results_count": session_data.get("results_count", 0),
            "metadata": session_data.get("metadata", {})
        }

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list) and len(response) > 0:
                item = response[0]
                if isinstance(item, dict):
                     # Handle different response formats
                    if 'id' in item:
                        return item['id']
                    if 'result' in item and isinstance(item['result'], list) and len(item['result']) > 0:
                        return item['result'][0].get('id')
            return ""

    async def get_user_sessions(self, user_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieve past search sessions for a user."""
        query = """
        SELECT * FROM search_session
        WHERE user_id = $user_id
        ORDER BY timestamp DESC
        LIMIT $limit;
        """
        params = {"user_id": user_id, "limit": limit}
        
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                return response
            return []

    async def create_search_feedback(self, session_id: str, memory_id: str, query_text: str, score: float) -> str:
        """Create a new search feedback record.

        Args:
            session_id: ID of the search session
            memory_id: ID of the memory that received feedback
            query_text: The search query
            score: Feedback score (e.g. 1.0 for click, -1.0 for negative)
        """
        query = """
        CREATE search_feedback CONTENT {
            session_id: $session_id,
            memory_id: $memory_id,
            query: $query,
            score: $score,
            created_at: time::now()
        };
        """
        params = {
            "session_id": session_id,
            "memory_id": memory_id,
            "query": query_text,
            "score": score
        }
        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list) and len(response) > 0:
                item = response[0]
                if isinstance(item, dict):
                    if 'id' in item:
                        return item['id']
                    if 'result' in item and isinstance(item['result'], list) and len(item['result']) > 0:
                        return item['result'][0].get('id')
            return ""

    async def get_feedback_for_query(self, query_text: str) -> List[Dict[str, Any]]:
        """Get aggregated feedback for a query.

        Returns memories that have positive feedback for this query.
        """
        # Exact match on query for now
        query = """
        SELECT memory_id, math::sum(score) as total_score
        FROM search_feedback
        WHERE query = $query
        GROUP BY memory_id
        HAVING total_score > 0
        ORDER BY total_score DESC;
        """
        params = {"query": query_text}

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                    return response[0]['result']
                return response
            return []
    async def get_search_suggestions(self, prefix: str, limit: int = 10) -> List[str]:
        """Get search suggestions based on past successful queries (Strategy 101)."""
        # We search for queries starting with the prefix
        # and we aggregate to get unique queries, perhaps sorting by frequency (count)
        # SurrealDB doesn't have a simple GROUP BY COUNT on the fly easily without defining a view mostly.
        # But we can select distinct queries.

        # Using a simple SELECT DISTINCT with basic filtering
        # Note: 'string::starts_with' is useful here.

        query = """
        SELECT query, count() as frequency FROM search_session
        WHERE string::starts_with(string::lowercase(query), string::lowercase($prefix))
        GROUP BY query
        ORDER BY frequency DESC
        LIMIT $limit;
        """

        params = {
            "prefix": prefix,
            "limit": limit
        }

        async with self.get_connection() as conn:
            response = await conn.query(query, params)

            suggestions = []
            if response and isinstance(response, list):
                items = response
                if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']

                for item in items:
                    if isinstance(item, dict) and 'query' in item:
                        suggestions.append(item['query'])

            return suggestions

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

    async def update_relationship_weight(self, relationship_id: str, new_weight: float) -> None:
        """Update the weight of a relationship (Task 68).

        Args:
            relationship_id: The ID of the relationship to update.
            new_weight: The new weight value.
        """
        if ":" in relationship_id:
            relationship_id = relationship_id.split(":")[1]

        query = """
        UPDATE type::thing('relationship', $id)
        SET weight = $weight,
            updated_at = time::now();
        """
        params = {"id": relationship_id, "weight": new_weight}

        async with self.get_connection() as conn:
            await conn.query(query, params)

    async def archive_relationship(self, relationship_id: str) -> None:
        """Soft-delete a relationship by setting valid_to to now.

        Strategy 67 & 119: Temporal Edge Invalidation / Bi-temporal Graph.
        """
        # Strip ID prefix if present
        if ":" in relationship_id:
            relationship_id = relationship_id.split(":")[1]

        query = """
        UPDATE type::thing('relationship', $id)
        SET valid_to = time::now(),
            transaction_time_end = time::now();
        """
        params = {"id": relationship_id}

        async with self.get_connection() as conn:
            await conn.query(query, params)

    async def get_relationships_at_time(
        self,
        entity_id: str,
        timestamp: "datetime"
    ) -> List[Dict[str, Any]]:
        """Query relationships valid at a specific point in time (Time Travel).

        Strategy 67: Temporal Graph (Bi-temporal).
        """
        # Ensure entity_id format
        if ":" in entity_id:
             entity_id = entity_id.split(":")[1]

        query = """
        SELECT * FROM relationship
        WHERE (from_entity_id = $entity_id OR to_entity_id = $entity_id)
        AND valid_from <= $timestamp
        AND (valid_to IS NONE OR valid_to > $timestamp);
        """

        params = {
            "entity_id": entity_id,
            "timestamp": timestamp.isoformat()
        }

        async with self.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                 # Handle nested response
                 if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     return response[0]['result']
                 return response
            return []

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
