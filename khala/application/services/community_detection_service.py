"""Community Detection Service (Module 12.C.3).

Implements graph clustering algorithms (Label Propagation) to find communities in the knowledge graph.
Strategy 143.
"""

import logging
from typing import List, Dict, Any, Optional
from collections import Counter
import random
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class CommunityDetectionService:
    """Service for detecting communities in the graph."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def detect_communities(self, user_id: Optional[str] = None) -> Dict[str, int]:
        """
        Run community detection using Label Propagation Algorithm (LPA).
        Returns a mapping of entity_id -> community_id.
        """
        # 1. Fetch Graph
        snapshot = await self.db_client.get_graph_snapshot(user_id)

        entities = snapshot.get("entities", [])
        relationships = snapshot.get("relationships", [])

        if not entities:
            return {}

        # Build Adjacency List
        # Node ID -> List of Neighbor IDs
        adj: Dict[str, List[str]] = {str(e['id']).replace('entity:', ''): [] for e in entities}

        for r in relationships:
            # Handle SurrealDB record links
            u = str(r['from_entity_id']).replace('entity:', '')
            v = str(r['to_entity_id']).replace('entity:', '')

            # Add undirected edges for community detection
            if u in adj:
                adj[u].append(v)
            # Ensure v is in adj if it exists in entities
            if v in adj:
                adj[v].append(u)
            elif v not in adj:
                # If v is not in entities list (maybe incomplete snapshot), ignore or add?
                # For safety, we only track nodes we know exist in the fetch
                pass

        # 2. Initialize Labels
        # label[node_id] = distinct_id
        labels = {node: i for i, node in enumerate(adj.keys())}
        nodes = list(adj.keys())

        # 3. Iterate
        max_iter = 10
        for i in range(max_iter):
            changes = 0
            random.shuffle(nodes)

            for node in nodes:
                neighbors = adj.get(node, [])
                if not neighbors:
                    continue

                neighbor_labels = [labels[n] for n in neighbors if n in labels]
                if not neighbor_labels:
                    continue

                # Find most frequent label
                counts = Counter(neighbor_labels)
                max_count = max(counts.values())
                candidates = [l for l, c in counts.items() if c == max_count]

                new_label = random.choice(candidates)

                if labels[node] != new_label:
                    labels[node] = new_label
                    changes += 1

            logger.debug(f"Community Detection Iteration {i}: {changes} changes")
            if changes == 0:
                break

        return labels
