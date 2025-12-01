"""
Analytics Service for KHALA.

Implements strategies 109 and 110:
- Importance Distribution (109): Histogram of memory values over time.
- Graph Evolution Metrics (110): Tracking node/edge count growth.
"""

import logging
from typing import Dict, Any, List, Optional

from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class AnalyticsService:
    """Service to generate and store system analytics and metrics."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def generate_importance_distribution(self, user_id: str) -> None:
        """
        Strategy 109: Calculate and store importance distribution for a user.
        Generates a histogram of memory importance scores (0.0 - 1.0).
        """
        # Query all memory importance scores for the user
        query = "SELECT importance FROM memory WHERE user_id = $user_id AND is_archived = false;"
        params = {"user_id": user_id}

        try:
            async with self.db_client.get_connection() as conn:
                results = await conn.query(query, params)

            # Parse results
            importances = []
            data = results

            # Handle SurrealDB response structure
            if isinstance(results, list) and len(results) > 0:
                if isinstance(results[0], dict) and "result" in results[0]:
                    data = results[0]["result"]
                elif isinstance(results[0], dict) and "status" in results[0]:
                    # Possible error or different format
                    if results[0].get("status") != "OK":
                        logger.error(f"Error querying importance: {results}")
                        return
                    data = results[0].get("result", [])

            if not isinstance(data, list):
                data = []

            for item in data:
                if isinstance(item, dict) and "importance" in item:
                    val = item["importance"]
                    if val is not None:
                         importances.append(float(val))

            # Calculate histogram (10 bins: 0.0-0.1, ..., 0.9-1.0)
            distribution = {}
            # Initialize bins
            for i in range(10):
                key = f"{i/10:.1f}-{(i+1)/10:.1f}"
                distribution[key] = 0

            total_count = len(importances)
            total_sum = 0.0

            for score in importances:
                total_sum += score
                # Clamp to 0-9 for bin index
                bin_idx = min(int(score * 10), 9)
                key = f"{bin_idx/10:.1f}-{(bin_idx+1)/10:.1f}"
                distribution[key] += 1

            avg_importance = total_sum / total_count if total_count > 0 else 0.0

            # Store in metrics_importance table
            insert_query = """
            CREATE metrics_importance CONTENT {
                user_id: $user_id,
                timestamp: time::now(),
                distribution: $distribution,
                total_count: $total_count,
                avg_importance: $avg_importance
            };
            """
            insert_params = {
                "user_id": user_id,
                "distribution": distribution,
                "total_count": total_count,
                "avg_importance": avg_importance
            }

            async with self.db_client.get_connection() as conn:
                await conn.query(insert_query, insert_params)

            logger.info(f"Generated importance distribution for user {user_id}. Count: {total_count}")

        except Exception as e:
            logger.error(f"Failed to generate importance distribution: {e}")

    async def generate_graph_metrics(self, user_id: str = "global") -> None:
        """
        Strategy 110: Calculate and store graph evolution metrics.
        Tracks node (Entity) and edge (Relationship) counts and types.

        Currently calculates global metrics as Entity/Relationship tables are not partitioned by user_id
        in the current schema. The 'user_id' param is stored for reference but metrics are global.
        """
        try:
            # 1. Node counts (total and by type)
            # SurrealDB GROUP BY returns one record per group with aggregation results
            node_query = "SELECT count() as count, entity_type FROM entity GROUP BY entity_type;"

            # 2. Edge counts (total and by type)
            edge_query = "SELECT count() as count, relation_type FROM relationship GROUP BY relation_type;"

            async with self.db_client.get_connection() as conn:
                # Run node query
                node_results = await conn.query(node_query)
                # Run edge query
                edge_results = await conn.query(edge_query)

            # Helper to parse group by results
            def parse_group_results(results):
                data = results
                if isinstance(results, list) and len(results) > 0:
                     if isinstance(results[0], dict) and "result" in results[0]:
                         data = results[0]["result"]

                total = 0
                breakdown = {}

                if isinstance(data, list):
                    for item in data:
                        # item e.g. {"entity_type": "person", "count": 10}
                        count = 0
                        if "count" in item:
                            count = int(item["count"])

                        group_key = "unknown"
                        if "entity_type" in item:
                            group_key = item["entity_type"]
                        elif "relation_type" in item:
                            group_key = item["relation_type"]

                        breakdown[group_key] = count
                        total += count
                return total, breakdown

            node_count, entity_counts = parse_group_results(node_results)
            edge_count, relation_counts = parse_group_results(edge_results)

            avg_degree = 0.0
            if node_count > 0:
                # Average Degree (Directed) = Edges / Nodes
                avg_degree = edge_count / node_count

            # Store in metrics_graph table
            insert_query = """
            CREATE metrics_graph CONTENT {
                user_id: $user_id,
                timestamp: time::now(),
                node_count: $node_count,
                edge_count: $edge_count,
                avg_degree: $avg_degree,
                entity_counts: $entity_counts,
                relation_counts: $relation_counts
            };
            """

            insert_params = {
                "user_id": user_id,
                "node_count": node_count,
                "edge_count": edge_count,
                "avg_degree": avg_degree,
                "entity_counts": entity_counts,
                "relation_counts": relation_counts
            }

            async with self.db_client.get_connection() as conn:
                await conn.query(insert_query, insert_params)

            logger.info(f"Generated graph metrics. Nodes: {node_count}, Edges: {edge_count}")

        except Exception as e:
            logger.error(f"Failed to generate graph metrics: {e}")
