from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass

from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

@dataclass
class DependencyImpact:
    """Represents the impact of modifying/deleting a dependency."""
    memory_id: str
    impact_level: str  # 'critical', 'warning', 'info'
    description: str

class DependencyService:
    """
    Service for tracking and analyzing dependencies between memories (Strategy 155).
    Uses the generic 'relationship' table with specific types.
    """

    DEPENDENCY_TYPE = "DEPENDS_ON"
    CODE_DEPENDENCY_TYPE = "CODE_DEPENDENCY"

    def __init__(self, db_client: Optional[SurrealDBClient] = None):
        self.db_client = db_client or SurrealDBClient()

    async def add_dependency(
        self,
        source_id: str,
        target_id: str,
        dep_type: str = "DEPENDS_ON",
        weight: float = 1.0
    ) -> str:
        """
        Add a dependency: source DEPENDS_ON target.

        Args:
            source_id: The dependent memory ID (e.g., function A).
            target_id: The dependency memory ID (e.g., library B).
            dep_type: Type of dependency (e.g., 'CODE_DEPENDENCY', 'LOGICAL').
            weight: Strength/Importance of dependency.

        Returns:
            Relationship ID.
        """
        # Ensure IDs are formatted correctly (record links)
        # Assuming relationship table expects 'in' and 'out' as record IDs.
        # But schema uses 'from_entity_id' string fields for easier querying in some contexts,
        # and 'in'/'out' for graph traversal.

        # We need to construct the RELATION query
        # RELATE source->relationship->target

        # NOTE: source_id and target_id might need 'memory:' prefix if they are raw UUIDs
        # but the caller usually provides the full ID.

        try:
            query = """
            RELATE $source->relationship->$target CONTENT {
                relation_type: $type,
                from_entity_id: $source_id,
                to_entity_id: $target_id,
                weight: $weight,
                created_at: time::now(),
                valid_from: time::now()
            };
            """

            params = {
                "source": source_id,
                "target": target_id,
                "type": dep_type,
                "source_id": source_id,
                "target_id": target_id,
                "weight": weight
            }

            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, params)
                # Parse result to get ID
                if result and isinstance(result, list) and result[0].get('result'):
                    return result[0]['result'][0]['id']
                return ""

        except Exception as e:
            logger.error(f"Failed to add dependency {source_id} -> {target_id}: {e}")
            raise

    async def get_dependencies(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        Get list of memories that this memory depends on.
        (Outbound edges: memory -> DEPENDS_ON -> other)
        """
        try:
            # We want to find targets where this memory is the source
            query = """
            SELECT out, to_entity_id, relation_type, weight
            FROM relationship
            WHERE from_entity_id = $id
            AND (relation_type = $type1 OR relation_type = $type2);
            """

            params = {
                "id": memory_id,
                "type1": self.DEPENDENCY_TYPE,
                "type2": self.CODE_DEPENDENCY_TYPE
            }

            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, params)
                if result and isinstance(result, list):
                    return result[0].get('result', [])
                return []

        except Exception as e:
            logger.error(f"Failed to get dependencies for {memory_id}: {e}")
            return []

    async def get_dependents(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        Get list of memories that depend on this memory.
        (Inbound edges: other -> DEPENDS_ON -> memory)
        """
        try:
            # We want to find sources where this memory is the target
            query = """
            SELECT in, from_entity_id, relation_type, weight
            FROM relationship
            WHERE to_entity_id = $id
            AND (relation_type = $type1 OR relation_type = $type2);
            """

            params = {
                "id": memory_id,
                "type1": self.DEPENDENCY_TYPE,
                "type2": self.CODE_DEPENDENCY_TYPE
            }

            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, params)
                if result and isinstance(result, list):
                    return result[0].get('result', [])
                return []

        except Exception as e:
            logger.error(f"Failed to get dependents for {memory_id}: {e}")
            return []

    async def check_impact_analysis(self, memory_id: str) -> List[DependencyImpact]:
        """
        Analyze impact of modifying/deleting a memory.
        Returns a list of impacted components.
        """
        dependents = await self.get_dependents(memory_id)
        impacts = []

        for dep in dependents:
            # dep['in'] is the source record ID (the dependent)
            dependent_id = dep.get('from_entity_id') or dep.get('in')
            relation_type = dep.get('relation_type')

            level = "warning"
            desc = f"Depends on this memory via {relation_type}"

            if relation_type == self.CODE_DEPENDENCY_TYPE:
                level = "critical"
                desc = "Code execution might break"

            impacts.append(DependencyImpact(
                memory_id=str(dependent_id),
                impact_level=level,
                description=desc
            ))

        return impacts
