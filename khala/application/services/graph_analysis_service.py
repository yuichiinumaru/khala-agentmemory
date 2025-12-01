"""Service for algorithmic detection of graph motifs (Strategy 74).

This service analyzes the knowledge graph to find patterns like star topologies,
dense clusters, and long chains.
"""

import logging
from typing import List, Dict, Any, Optional
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class GraphAnalysisService:
    """Service for graph topology analysis and motif detection."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def detect_star_patterns(self, min_degree: int = 5) -> List[Dict[str, Any]]:
        """
        Detect star topologies: nodes with a high degree of outgoing or incoming connections.

        Args:
            min_degree: Minimum number of connections to qualify as a star center.

        Returns:
            List of nodes acting as hubs/stars with their degree count.
        """
        # SurrealDB query to count relationships per entity
        # We look for entities that appear in 'from_entity_id' or 'to_entity_id' many times.
        # Note: This is a simplified view. A true star might be directed or undirected.

        query = """
        SELECT
            id,
            text,
            entity_type,
            (SELECT count() FROM relationship WHERE from_entity_id = $parent.id) as out_degree,
            (SELECT count() FROM relationship WHERE to_entity_id = $parent.id) as in_degree
        FROM entity
        WHERE
            (SELECT count() FROM relationship WHERE from_entity_id = $parent.id) >= $min_degree
            OR
            (SELECT count() FROM relationship WHERE to_entity_id = $parent.id) >= $min_degree
        ORDER BY out_degree + in_degree DESC;
        """

        params = {"min_degree": min_degree}

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query, params)
                if response and isinstance(response, list):
                     # Handle nested response structure
                    if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                        return response[0]['result']
                    return response
                return []
        except Exception as e:
            logger.error(f"Error detecting star patterns: {e}")
            return []

    async def detect_chains(self, min_length: int = 3) -> List[Dict[str, Any]]:
        """
        Detect long chains of relationships A -> B -> C.

        Args:
            min_length: Minimum length of the chain (currently fixed at 3 nodes for this optimization).

        Returns:
            List of chains found (start_node, node_2, node_3).
        """
        # Implementing a fixed 3-hop chain detection using nested selects.
        # This query finds paths A -> B -> C where relationships exist.

        query = """
        SELECT
            in.id as start_node,
            out.id as node_2,
            (SELECT out.id FROM relationship WHERE in.id = $parent.out.id LIMIT 1) as node_3
        FROM relationship
        WHERE
            count((SELECT out.id FROM relationship WHERE in.id = $parent.out.id LIMIT 1)) > 0;
        """

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query)
                if response and isinstance(response, list):
                    if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                        # Filter to ensure we have actual chains (not None)
                        results = response[0]['result']
                        chains = [r for r in results if r.get('node_3') and len(r['node_3']) > 0]
                        return chains
                    return response
                return []
        except Exception as e:
            logger.error(f"Error detecting chains: {e}")
            return []

    async def detect_dense_clusters(self, min_size: int = 3) -> List[Dict[str, Any]]:
        """
        Detect dense clusters (cliques or near-cliques) where entities are highly interconnected.

        Args:
            min_size: Minimum number of nodes in the cluster.
        """
        # This usually requires running a community detection algorithm (Strategy 143).
        # For "Pattern Discovery" (74), we can look for triangles (A->B, B->C, C->A).

        query = """
        SELECT
            in as a,
            out as b,
            (SELECT out FROM relationship WHERE in = $parent.out AND out = $parent.in) as closed_loop
        FROM relationship
        WHERE (SELECT count() FROM relationship WHERE in = $parent.out AND out = $parent.in) > 0;
        """

        # This finds pairs with bidirectional links.
        # Finding triangles:

        query_triangles = """
        SELECT
            in.id as node_a,
            out.id as node_b,
            (SELECT out.id FROM relationship WHERE in.id = $parent.out.id AND out.id = $parent.in.id) as node_c -- This is actually closing back to A? No.
        FROM relationship;
        """

        # Correct triangle logic: A->B, B->C, C->A
        # SurrealQL allows subqueries.

        query = """
        SELECT
            in.id as a,
            out.id as b,
            (SELECT out.id FROM relationship WHERE in.id = $parent.out.id AND
                out.id IN (SELECT in.id FROM relationship WHERE out.id = $parent.in.id)
            ) as c
        FROM relationship
        WHERE count((SELECT out.id FROM relationship WHERE in.id = $parent.out.id AND
                out.id IN (SELECT in.id FROM relationship WHERE out.id = $parent.in.id)
            )) > 0;
        """

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query)
                if response and isinstance(response, list):
                    if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                        return response[0]['result']
                    return response
                return []
        except Exception as e:
            logger.error(f"Error detecting clusters: {e}")
            return []

    async def get_graph_metrics(self) -> Dict[str, Any]:
        """Get overall graph metrics."""
        query = """
        SELECT
            count() as edge_count,
            math::mean(strength) as avg_strength,
            count(relation_type) as type_counts
        FROM relationship
        GROUP BY ALL;
        """

        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query)
                # Process response
                return {"metrics": response}
        except Exception as e:
            return {"error": str(e)}
