"""Graph service for advanced graph operations."""
import logging
import uuid
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from khala.domain.memory.entities import Entity, Relationship, EntityType
from khala.domain.memory.repository import MemoryRepository
from khala.infrastructure.cache.cache_manager import CacheManager

logger = logging.getLogger(__name__)

class GraphService:
    """Service for advanced graph operations like hyperedges and inheritance."""

    def __init__(self, repository: MemoryRepository, cache_manager: Optional[CacheManager] = None):
        self.repository = repository
        self.cache_manager = cache_manager

    async def create_hyperedge(
        self,
        entities: List[str],
        edge_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Create a hyperedge connecting multiple entities.
        """
        # 1. Create the HyperNode
        hyper_node = Entity(
            text=f"Hyperedge: {edge_type}",
            entity_type=EntityType.EVENT,
            confidence=1.0,
            metadata={
                "is_hyperedge": True,
                "hyperedge_type": edge_type,
                **(metadata or {})
            }
        )

        # Access client to save entity
        if hasattr(self.repository, 'client'):
             await self.repository.client.create_entity(hyper_node)
        else:
             logger.error("Repository does not have client access for entity creation")
             raise RuntimeError("Repository client not available")

        # 2. Create edges from all entities to the HyperNode
        for entity_id in entities:
            rel = Relationship(
                from_entity_id=entity_id,
                to_entity_id=hyper_node.id,
                relation_type="PARTICIPANT",
                strength=1.0
            )
            if hasattr(self.repository, 'client'):
                await self.repository.client.create_relationship(rel)

        return hyper_node.id

    async def get_inherited_relationships(self, entity_id: str) -> List[Relationship]:
        """
        Get all relationships for an entity, including those inherited from parents.

        Inheritance is defined by 'is_a' or 'subclass_of' relationships.
        """
        client = getattr(self.repository, 'client', None)
        if not client:
            logger.error("Repository does not have client access")
            return []

        # 1. Get direct relationships (where entity is source)
        query = "SELECT * FROM relationship WHERE from_entity_id = $id;"
        params = {"id": entity_id}

        direct_rels = []
        async with client.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list):
                 # Handle response structure (might be list of dicts directly or wrapped in result)
                 items = response
                 if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     # This handles the case where SurrealDB returns [{'result': [...], 'status': 'OK'}]
                     if response[0]['status'] == 'OK':
                        items = response[0]['result']
                     else:
                        items = []

                 for item in items:
                     if isinstance(item, dict):
                        direct_rels.append(self._deserialize_relationship(item))

        # 2. Find parents (entities this entity 'is_a' or 'subclass_of')
        query_parents = """
        SELECT to_entity_id
        FROM relationship
        WHERE from_entity_id = $id
        AND (relation_type = 'is_a' OR relation_type = 'subclass_of');
        """

        parents = []
        async with client.get_connection() as conn:
            response = await conn.query(query_parents, params)
            items = response
            if response and isinstance(response, list) and len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                 if response[0]['status'] == 'OK':
                    items = response[0]['result']
                 else:
                    items = []

            for item in items:
                if isinstance(item, dict) and 'to_entity_id' in item:
                    parents.append(item['to_entity_id'])

        inherited_rels = []
        for parent_id in parents:
            # Get parent's relationships
            query_parent_rels = "SELECT * FROM relationship WHERE from_entity_id = $id;"
            parent_params = {"id": parent_id}

            async with client.get_connection() as conn:
                response = await conn.query(query_parent_rels, parent_params)
                items = response
                if response and isinstance(response, list) and len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     if response[0]['status'] == 'OK':
                        items = response[0]['result']
                     else:
                        items = []

                for item in items:
                    if isinstance(item, dict):
                        parent_rel = self._deserialize_relationship(item)
                        # We do not inherit the inheritance relationship itself
                        if parent_rel.relation_type in ['is_a', 'subclass_of']:
                            continue

                        # Create a virtual relationship from child
                        inherited_rel = Relationship(
                            from_entity_id=entity_id,
                            to_entity_id=parent_rel.to_entity_id,
                            relation_type=parent_rel.relation_type,
                            strength=parent_rel.strength,
                            valid_from=parent_rel.valid_from,
                            valid_to=parent_rel.valid_to,
                            transaction_time_start=datetime.now(timezone.utc)
                        )
                        # Mark as inherited (conceptually, not in schema unless we add metadata field)
                        inherited_rels.append(inherited_rel)

        return direct_rels + inherited_rels

    async def get_entity_descendants(
        self,
        entity_id: str,
        relation_type: str = "PARTICIPANT",
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """
        Get all descendants of an entity using recursive graph traversal.

        Strategy 71: Recursive Graph Patterns.
        Strategy 122: Path Lookup Acceleration (Cache).
        Strategy 124: Multi-Hop Constraints (Max Depth).
        """
        # Task 124: Multi-Hop Constraints
        if max_depth > 3:
            logger.warning(f"Max depth {max_depth} exceeds limit 3. Clamping to 3.")
            max_depth = 3

        # Task 122: Path Lookup Acceleration (Check Cache)
        cache_key = ""
        if self.cache_manager:
            cache_key = self.cache_manager.generate_cache_key("descendants", entity_id, relation_type, max_depth)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for descendants of {entity_id}")
                return cached_result

        client = getattr(self.repository, 'client', None)
        if not client:
            logger.error("Repository does not have client access")
            return []

        # Use the custom SurrealDB function defined in schema
        # fn::get_descendants(start_node string, relation_type string, max_depth int)
        query = "RETURN fn::get_descendants($start_node, $relation_type, $max_depth);"
        params = {
            "start_node": entity_id,
            "relation_type": relation_type,
            "max_depth": max_depth
        }

        try:
            async with client.get_connection() as conn:
                response = await conn.query(query, params)
                # Parse response
                result = []
                if response and isinstance(response, list):
                     if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                        # The function returns a specific structure, we might need to flatten it
                        # depending on how fn::get_descendants is implemented in schema.
                        # Schema: RETURN SELECT *, (SELECT * FROM relationship...) AS children
                        result = response[0]['result']
                     else:
                        result = response

                # Cache result
                if self.cache_manager and result:
                     # Cache for 1 hour (3600s)
                     await self.cache_manager.put(cache_key, result, ttl_seconds=3600)

                return result

        except Exception as e:
            logger.error(f"Recursive graph traversal failed: {e}")

        return []

    def _deserialize_relationship(self, data: Dict[str, Any]) -> Relationship:
        """Helper to deserialize relationship data."""
        def parse_dt(dt_val: Any) -> Optional[datetime]:
            if not dt_val: return None
            if isinstance(dt_val, str):
                if dt_val.endswith('Z'): dt_val = dt_val[:-1]
                return datetime.fromisoformat(dt_val).replace(tzinfo=timezone.utc)
            return dt_val

        rel_id = str(data["id"])
        if rel_id.startswith("relationship:"):
            rel_id = rel_id.split(":", 1)[1]

        return Relationship(
            id=rel_id,
            from_entity_id=data["from_entity_id"],
            to_entity_id=data["to_entity_id"],
            relation_type=data["relation_type"],
            strength=data["strength"],
            valid_from=parse_dt(data.get("valid_from")) or datetime.now(timezone.utc),
            valid_to=parse_dt(data.get("valid_to")),
            transaction_time_start=parse_dt(data.get("transaction_time_start")) or datetime.now(timezone.utc),
            transaction_time_end=parse_dt(data.get("transaction_time_end"))
        )
