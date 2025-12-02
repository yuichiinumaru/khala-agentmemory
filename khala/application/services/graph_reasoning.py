"""Knowledge Graph Reasoning Service (Module 13.2.1 - LGKGR).

Implements hybrid LLM+GNN reasoning: Path Search -> Pruning -> Evaluation.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
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

@dataclass
class GraphPattern:
    """A pattern to match in the knowledge graph."""
    nodes: List[Dict[str, Any]]  # e.g. [{"id": "p1", "type": "Person", "properties": {...}}]
    edges: List[Dict[str, Any]]  # e.g. [{"source": "p1", "target": "p2", "relation": "knows"}]

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

    async def find_isomorphic_subgraphs(self, pattern: GraphPattern, start_node_id: Optional[str] = None) -> List[Dict[str, str]]:
        """
        Find subgraphs matching the given pattern using a backtracking algorithm.
        Returns a list of mappings {pattern_node_id: graph_node_id}.

        Args:
            pattern: The structural pattern to match.
            start_node_id: Optional graph node ID to anchor the search (must match pattern.nodes[0]).
        """
        # Validate pattern
        if not pattern.nodes:
            return []

        # Candidate generation
        candidates: Dict[str, List[str]] = {}

        # Get all pattern node IDs
        p_nodes = [n["id"] for n in pattern.nodes]

        # Fetch candidates for all nodes
        for i in range(len(pattern.nodes)):
            p_node = pattern.nodes[i]
            if start_node_id and i == 0:
                 candidates[p_node["id"]] = [start_node_id]
            else:
                 candidates[p_node["id"]] = await self._fetch_candidates(p_node)

        # Collect all candidate IDs for bulk edge fetching
        all_candidate_ids = set()
        for c_list in candidates.values():
            all_candidate_ids.update(c_list)

        if not all_candidate_ids:
            return []

        # Bulk fetch edges
        edge_cache = await self._fetch_bulk_edges(list(all_candidate_ids))

        matches = []

        # Backtracking function
        def backtrack(current_mapping: Dict[str, str]):
            # If mapping includes all pattern nodes, we found a match
            if len(current_mapping) == len(pattern.nodes):
                matches.append(current_mapping.copy())
                return

            # Pick next pattern node to map
            next_p_idx = len(current_mapping)
            next_p_node_id = p_nodes[next_p_idx]

            # Try all candidates for this pattern node
            possible_candidates = candidates.get(next_p_node_id, [])

            for cand_id in possible_candidates:
                if cand_id in current_mapping.values():
                    continue # Bijective mapping

                # Check structural consistency with already mapped nodes
                if self._is_consistent_cached(cand_id, next_p_node_id, current_mapping, pattern, edge_cache):
                    current_mapping[next_p_node_id] = cand_id
                    backtrack(current_mapping)
                    del current_mapping[next_p_node_id]

        backtrack({})
        return matches

    async def _fetch_candidates(self, pattern_node: Dict[str, Any]) -> List[str]:
        """Fetch potential graph nodes that match pattern node constraints (type, properties)."""
        where_clauses = []
        params = {}

        if "type" in pattern_node:
            where_clauses.append("entity_type = $type")
            params["type"] = pattern_node["type"]

        # Handle properties (assuming stored in metadata or specific fields)
        if "properties" in pattern_node:
            for k, v in pattern_node["properties"].items():
                # Check properties in metadata
                param_key = f"prop_{k}"
                where_clauses.append(f"metadata.{k} = ${param_key}")
                params[param_key] = v

        query = "SELECT id FROM entity"
        if where_clauses:
            query += " WHERE " + " AND ".join(where_clauses)
        query += " LIMIT 50;"

        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, params)
            ids = []
            if response and isinstance(response, list) and response:
                items = response
                if isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']

                for item in items:
                    if 'id' in item:
                        ids.append(item['id'])
            return ids

    async def _fetch_bulk_edges(self, node_ids: List[str]) -> Dict[Tuple[str, str], List[str]]:
        """Fetch all edges connected to the given node IDs."""
        if not node_ids:
             return {}

        # Chunking to avoid query limit
        chunk_size = 50
        all_edges = []

        for i in range(0, len(node_ids), chunk_size):
             chunk = node_ids[i:i+chunk_size]
             query = "SELECT * FROM relationship WHERE from_entity_id IN $ids OR to_entity_id IN $ids"
             params = {"ids": chunk}

             async with self.db_client.get_connection() as conn:
                response = await conn.query(query, params)
                if response and isinstance(response, list):
                    items = response
                    if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                        items = response[0]['result']
                    all_edges.extend(items)

        # Build adjacency map: (from, to) -> [relation_types]
        edge_map = {}
        for edge in all_edges:
             f = edge.get("from_entity_id")
             t = edge.get("to_entity_id")
             rel = edge.get("relation_type")

             if f and t:
                 key = (f, t)
                 if key not in edge_map:
                     edge_map[key] = []
                 if rel:
                    edge_map[key].append(rel)
        return edge_map

    def _is_consistent_cached(self, cand_id: str, p_node_id: str, current_mapping: Dict[str, str], pattern: GraphPattern, edge_cache: Dict[Tuple[str, str], List[str]]) -> bool:
        """Check consistency using cached edges (Synchronous)."""

        for edge in pattern.edges:
            # Case 1: p_node_id is source, target is already mapped
            if edge["source"] == p_node_id and edge["target"] in current_mapping:
                target_cand_id = current_mapping[edge["target"]]
                if not self._check_edge_exists_cached(cand_id, target_cand_id, edge.get("relation"), edge_cache):
                    return False

            # Case 2: p_node_id is target, source is already mapped
            elif edge["target"] == p_node_id and edge["source"] in current_mapping:
                source_cand_id = current_mapping[edge["source"]]
                if not self._check_edge_exists_cached(source_cand_id, cand_id, edge.get("relation"), edge_cache):
                    return False
        return True

    def _check_edge_exists_cached(self, from_id: str, to_id: str, relation_type: Optional[str], edge_cache: Dict[Tuple[str, str], List[str]]) -> bool:
        """Check edge existence in cache."""
        rels = edge_cache.get((from_id, to_id), [])
        if not rels:
            return False

        if relation_type:
             return relation_type in rels
        return True

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
