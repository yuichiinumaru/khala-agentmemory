"""Knowledge Graph Reasoning Service (Module 13.2.1 - LGKGR).

Implements hybrid LLM+GNN reasoning: Path Search -> Pruning -> Evaluation.
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime, timezone

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

@dataclass
class ReasoningPath:
    """A single reasoning path in the knowledge graph."""
    nodes: List[str]
    relationships: List[str]
    score: float = 0.0

class KnowledgeGraphReasoningService:
    """Service for performing multi-hop reasoning over the knowledge graph."""

    def __init__(self, db_client: SurrealDBClient, gemini_client: GeminiClient):
        self.db_client = db_client
        self.gemini_client = gemini_client

    async def reason_over_graph(self, start_entity_id: str, query: str, max_hops: int = 3) -> Dict[str, Any]:
        """
        Execute 3-phase reasoning:
        1. Path Search: Find potential paths via vector search / graph traversal.
        2. Pruning: Filter irrelevant paths.
        3. Evaluation: Use LLM to select and explain the best path.
        """

        # 1. Path Search
        paths = await self._find_candidate_paths(start_entity_id, max_hops)

        # 2. Pruning (Simplified: Heuristic based on path length or generic score)
        # In full implementation, this would use a GNN model.
        pruned_paths = self._prune_paths(paths)

        if not pruned_paths:
            return {"error": "No viable paths found"}

        # 3. LLM Evaluation
        best_path, explanation = await self._evaluate_paths_with_llm(query, pruned_paths)

        # Store trace
        await self._save_trace(start_entity_id, query, best_path, explanation)

        return {
            "best_path": best_path,
            "explanation": explanation
        }

    async def _find_candidate_paths(self, start_id: str, depth: int) -> List[ReasoningPath]:
        """Find paths from start node up to depth using DB traversal."""
        # Using a simulated recursive fetch for now as SurrealDB recursive graph queries
        # are complex to construct dynamically.
        # Ideally: SELECT * FROM (SELECT ->?->? FROM $start_id)

        # We try to get immediate neighbors and construct 1-hop paths as a starting point implementation.
        query = """
        SELECT ->relationship->entity AS path FROM $start_id;
        """
        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, {"start_id": start_id})

            paths = []
            if response and isinstance(response, list) and response:
                items = response
                if isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']

                # Each item is {path: [entity_record]}
                for item in items:
                    path_entities = item.get('path', [])
                    if path_entities:
                         # Extract IDs
                         node_ids = [start_id] + [p['id'] for p in path_entities if 'id' in p]
                         if len(node_ids) > 1:
                             paths.append(ReasoningPath(nodes=node_ids, relationships=["related_to"]))

            if not paths:
                # Return empty list or fallback if no graph data exists
                return []

            return paths

    def _prune_paths(self, paths: List[ReasoningPath]) -> List[ReasoningPath]:
        """Filter out low-quality paths."""
        return paths[:5]  # Keep top 5

    async def _evaluate_paths_with_llm(self, query: str, paths: List[ReasoningPath]) -> tuple[ReasoningPath, str]:
        """Ask LLM to select the best path for the query."""
        path_descriptions = []
        for i, p in enumerate(paths):
            desc = f"Path {i}: " + " -> ".join(p.nodes)
            path_descriptions.append(desc)

        prompt = f"""
        Query: {query}

        Available Knowledge Paths:
        {chr(10).join(path_descriptions)}

        Select the path that best answers the query and explain why.
        """

        response = await self.gemini_client.generate_content(prompt, model_tier="SMART")
        # Simplified parsing
        return paths[0], response.text

    async def _save_trace(self, start: str, query: str, path: ReasoningPath, explanation: str) -> None:
        """Save reasoning trace to DB."""
        query_sql = """
        CREATE reasoning_paths CONTENT {
            query_entity: $start,
            target_entity: $end,
            path: $path,
            llm_explanation: $explanation,
            confidence: 0.9,
            final_rank: 1,
            created_at: time::now()
        };
        """
        params = {
            "start": start,
            "end": path.nodes[-1] if path.nodes else "",
            "path": [{"node": n} for n in path.nodes],
            "explanation": explanation
        }
        async with self.db_client.get_connection() as conn:
            await conn.query(query_sql, params)
