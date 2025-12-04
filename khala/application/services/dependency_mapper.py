from typing import List, Dict, Any, Set
import logging
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class DependencyMapper:
    """
    Service for tracking and analyzing dependencies between memories.
    Strategy 155: Dependency Mapping.
    """
    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def get_dependencies(self, memory_id: str, depth: int = 1) -> List[Dict[str, Any]]:
        """
        Get all memories that the given memory depends on (outgoing edges).
        """
        # Logic: memory -> depends_on -> other_memory
        # Assuming we use a 'depends_on' relationship type
        query = f"""
        SELECT out, out.content as content, out.id as id FROM relationship
        WHERE in = $memory_id AND type = 'depends_on';
        """

        # This is a simplified query. Graph traversal in SurrealDB 2.0 uses specific syntax.
        # SELECT ->depends_on->memory FROM memory WHERE id = $id

        # Let's use a mocked logic if we can't run real graph queries easily without testing schema.
        # But we should try to use the client correctly.

        clean_id = memory_id if not memory_id.startswith("memory:") else memory_id

        async with self.db_client.get_connection() as conn:
            # Using basic relationship selection
            result = await conn.query(query, {"memory_id": clean_id})
            # Process result...
            deps = []
            if result and isinstance(result, list) and len(result) > 0 and result[0].get('result'):
                for item in result[0]['result']:
                    deps.append(item)
            return deps

    async def get_dependents(self, memory_id: str) -> List[Dict[str, Any]]:
        """
        Get all memories that depend on the given memory (incoming edges).
        """
        query = f"""
        SELECT in, in.content as content, in.id as id FROM relationship
        WHERE out = $memory_id AND type = 'depends_on';
        """
        clean_id = memory_id if not memory_id.startswith("memory:") else memory_id

        async with self.db_client.get_connection() as conn:
            result = await conn.query(query, {"memory_id": clean_id})
            deps = []
            if result and isinstance(result, list) and len(result) > 0 and result[0].get('result'):
                for item in result[0]['result']:
                    deps.append(item)
            return deps

    async def analyze_impact(self, memory_id: str) -> Dict[str, Any]:
        """
        Analyze the impact of modifying or deleting a memory.
        """
        dependents = await self.get_dependents(memory_id)
        return {
            "direct_dependent_count": len(dependents),
            "dependents": dependents,
            "risk_level": "high" if len(dependents) > 5 else "low"
        }
