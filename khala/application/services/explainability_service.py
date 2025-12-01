from typing import List, Dict, Any, Optional
import logging
from datetime import datetime, timezone
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class ExplainabilityService:
    """
    Service for managing reasoning traces and explainability graphs (Strategy 76).
    """
    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def store_reasoning_trace(
        self,
        query_entity: str,
        target_entity: str,
        path: List[str],
        llm_explanation: str,
        confidence: float,
        final_rank: int
    ) -> str:
        """
        Store a reasoning trace in the database.

        Args:
            query_entity: The starting entity of the reasoning.
            target_entity: The conclusion entity.
            path: List of step descriptions or entity IDs in the trace.
            llm_explanation: Natural language explanation of the reasoning.
            confidence: Confidence score (0.0 - 1.0).
            final_rank: Rank of this reasoning path among alternatives.

        Returns:
            The ID of the stored reasoning path.
        """
        try:
            # Check if this path already exists to avoid duplicates?
            # For now, we assume each trace is unique to a request context, but we don't have request ID here.
            # We'll just create it.

            data = {
                "query_entity": query_entity,
                "target_entity": target_entity,
                "path": path,
                "llm_explanation": llm_explanation,
                "confidence": confidence,
                "final_rank": final_rank,
                "created_at": datetime.now(timezone.utc).isoformat()
            }

            # Using direct query as there might not be a repo for reasoning_paths yet
            # schema defines 'reasoning_paths' table

            async with self.db_client.get_connection() as conn:
                result = await conn.create("reasoning_paths", data)
                if result:
                    if isinstance(result, list):
                        return result[0]["id"]
                    return result["id"]
                return ""
        except Exception as e:
            logger.error(f"Failed to store reasoning trace: {e}")
            raise

    async def get_trace_as_graph(self, trace_id: str) -> Dict[str, Any]:
        """
        Retrieve a reasoning trace converted into a graph structure (Nodes/Edges).
        This facilitates the 'Explainability Graph' visualization.

        Args:
            trace_id: The ID of the reasoning path.

        Returns:
            Dictionary with 'nodes' and 'edges'.
        """
        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.select(trace_id)
                if not result:
                    return {}

                trace = result if not isinstance(result, list) else result[0]

            path = trace.get("path", [])
            nodes = []
            edges = []

            # Add Start Node (Query Entity)
            nodes.append({
                "id": "start",
                "label": trace.get("query_entity", "Query"),
                "type": "entity"
            })

            # Process Path Steps
            previous_node_id = "start"

            for i, step in enumerate(path):
                step_id = f"step_{i}"
                nodes.append({
                    "id": step_id,
                    "label": step,
                    "type": "step"
                })

                edges.append({
                    "from": previous_node_id,
                    "to": step_id,
                    "label": "next"
                })
                previous_node_id = step_id

            # Add End Node (Target Entity)
            nodes.append({
                "id": "end",
                "label": trace.get("target_entity", "Conclusion"),
                "type": "entity"
            })

            edges.append({
                "from": previous_node_id,
                "to": "end",
                "label": "concludes"
            })

            return {
                "trace_id": trace_id,
                "explanation": trace.get("llm_explanation", ""),
                "confidence": trace.get("confidence", 0.0),
                "graph": {
                    "nodes": nodes,
                    "edges": edges
                }
            }

        except Exception as e:
            logger.error(f"Failed to retrieve trace graph: {e}")
            return {}
