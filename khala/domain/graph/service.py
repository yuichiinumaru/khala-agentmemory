"""Graph service for advanced graph operations."""
import logging
import uuid
import asyncio
from typing import List, Optional, Dict, Any, Set
from datetime import datetime, timezone
import networkx as nx

from khala.domain.memory.entities import Entity, Relationship, EntityType
from khala.domain.memory.repository import MemoryRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class GraphService:
    """Service for advanced graph operations like hyperedges and inheritance."""

    def __init__(self, repository: MemoryRepository, db_client: Optional[SurrealDBClient] = None):
        self.repository = repository
        # Dependency Injection or extraction
        self.client = db_client
        if not self.client and hasattr(repository, 'client'):
            self.client = getattr(repository, 'client')

        if not self.client:
            logger.warning("GraphService initialized without SurrealDBClient. Advanced operations will fail.")

    def _require_client(self) -> SurrealDBClient:
        if not self.client:
            raise RuntimeError("SurrealDBClient is required for this operation.")
        return self.client

    async def create_hyperedge(
        self,
        entities: List[str],
        edge_type: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """Create a hyperedge connecting multiple entities."""
        client = self._require_client()

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

        await client.create_entity(hyper_node)

        for entity_id in entities:
            rel = Relationship(
                from_entity_id=entity_id,
                to_entity_id=hyper_node.id,
                relation_type="PARTICIPANT",
                strength=1.0
            )
            await client.create_relationship(rel)

        return hyper_node.id

    async def create_bitemporal_relationship(
        self,
        from_id: str,
        to_id: str,
        relation_type: str,
        valid_from: Optional[datetime] = None,
        valid_to: Optional[datetime] = None,
        strength: float = 1.0
    ) -> str:
        """Create a relationship with explicit bi-temporal validity."""
        client = self._require_client()

        if not valid_from:
            valid_from = datetime.now(timezone.utc)

        rel = Relationship(
            from_entity_id=from_id,
            to_entity_id=to_id,
            relation_type=relation_type,
            strength=strength,
            valid_from=valid_from,
            valid_to=valid_to,
            transaction_time_start=datetime.now(timezone.utc)
        )
        await client.create_relationship(rel)
        return rel.id

    async def invalidate_relationship(self, relationship_id: str) -> bool:
        """Soft-delete/invalidate a relationship by setting valid_to = now."""
        client = self._require_client()

        now = datetime.now(timezone.utc)
        query = "UPDATE relationship SET valid_to = $now WHERE id = $id OR id = $prefixed_id;"
        params = {
            "now": now,
            "id": relationship_id,
            "prefixed_id": f"relationship:{relationship_id}"
        }

        try:
            async with client.get_connection() as conn:
                await conn.query(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to invalidate relationship {relationship_id}: {e}")
            return False

    async def get_graph_snapshot(
        self,
        timestamp: datetime,
        limit: int = 1000
    ) -> nx.Graph:
        """Get a snapshot of the graph as it existed at `timestamp`."""
        client = self._require_client()

        query = """
        SELECT * FROM relationship
        WHERE valid_from <= $ts
        AND (valid_to IS NONE OR valid_to > $ts)
        LIMIT $limit;
        """
        params = {"ts": timestamp, "limit": limit}

        graph = nx.DiGraph()

        async with client.get_connection() as conn:
            response = await conn.query(query, params)
            rels = []
            if response and isinstance(response, list):
                 if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     rels = response[0]['result']
                 else:
                     rels = response

            for rel_data in rels:
                if isinstance(rel_data, dict):
                    graph.add_edge(
                        rel_data['from_entity_id'],
                        rel_data['to_entity_id'],
                        type=rel_data.get('relation_type'),
                        strength=rel_data.get('strength', 1.0)
                    )

        return graph

    async def get_inherited_relationships(self, entity_id: str) -> List[Relationship]:
        """Get all relationships for an entity, including those inherited from parents."""
        client = self._require_client()

        # 1. Get direct relationships
        query = """
        SELECT * FROM relationship
        WHERE from_entity_id = $id
        AND (valid_to IS NONE OR valid_to > time::now());
        """
        params = {"id": entity_id}

        direct_rels = []
        async with client.get_connection() as conn:
            response = await conn.query(query, params)
            items = []
            if response and isinstance(response, list):
                 if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     if response[0]['status'] == 'OK':
                        items = response[0]['result']
                 else:
                     items = response

            for item in items:
                if isinstance(item, dict):
                    direct_rels.append(self._deserialize_relationship(item))

        # 2. Find parents
        query_parents = """
        SELECT to_entity_id
        FROM relationship
        WHERE from_entity_id = $id
        AND (relation_type = 'is_a' OR relation_type = 'subclass_of')
        AND (valid_to IS NONE OR valid_to > time::now());
        """

        parents = []
        async with client.get_connection() as conn:
            response = await conn.query(query_parents, params)
            items = []
            if response and isinstance(response, list):
                 if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     if response[0]['status'] == 'OK':
                        items = response[0]['result']
                 else:
                     items = response

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
                items = []
                if response and isinstance(response, list):
                     if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                         if response[0]['status'] == 'OK':
                            items = response[0]['result']
                     else:
                         items = response

                for item in items:
                    if isinstance(item, dict):
                        parent_rel = self._deserialize_relationship(item)
                        if parent_rel.relation_type in ['is_a', 'subclass_of']:
                            continue

                        inherited_rel = Relationship(
                            from_entity_id=entity_id,
                            to_entity_id=parent_rel.to_entity_id,
                            relation_type=parent_rel.relation_type,
                            strength=parent_rel.strength,
                            valid_from=parent_rel.valid_from,
                            valid_to=parent_rel.valid_to,
                            transaction_time_start=datetime.now(timezone.utc)
                        )
                        inherited_rels.append(inherited_rel)

        return direct_rels + inherited_rels

    async def get_entity_descendants(
        self,
        entity_id: str,
        relation_type: str = "PARTICIPANT",
        max_depth: int = 3
    ) -> List[Dict[str, Any]]:
        """Get all descendants of an entity using recursive graph traversal."""
        client = self._require_client()

        query = "RETURN fn::get_descendants($start_node, $relation_type, $max_depth);"
        params = {
            "start_node": entity_id,
            "relation_type": relation_type,
            "max_depth": max_depth
        }

        try:
            async with client.get_connection() as conn:
                response = await conn.query(query, params)
                if response and isinstance(response, list):
                     if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                        return response[0]['result']
                     return response
        except Exception as e:
            logger.error(f"Recursive graph traversal failed: {e}")

        return []

    async def calculate_centrality(self, method: str = "degree", limit: int = 1000) -> Dict[str, float]:
        """Calculates centrality metrics. WARNING: In-memory processing."""
        client = self._require_client()

        # Strict limit to prevent OOM
        if limit > 2000:
            logger.warning(f"Centrality limit {limit} too high. Capping at 2000.")
            limit = 2000

        query = """
        SELECT * FROM relationship
        WHERE (valid_to IS NONE OR valid_to > time::now())
        LIMIT $limit;
        """
        params = {"limit": limit}

        # Build graph in thread to avoid blocking loop
        def _build_and_compute():
            graph = nx.Graph()
            # Fetching is async, this function is sync for computation.
            # We need to fetch first.
            return graph

        # We fetch first
        async with client.get_connection() as conn:
            response = await conn.query(query, params)
            rels = []
            if response and isinstance(response, list):
                 if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     rels = response[0]['result']
                 else:
                     rels = response

        if not rels:
            return {}

        def _compute(rel_data):
            g = nx.Graph()
            for r in rel_data:
                if isinstance(r, dict):
                    g.add_edge(r['from_entity_id'], r['to_entity_id'], weight=r.get('strength', 1.0))

            if method == "degree": return nx.degree_centrality(g)
            elif method == "betweenness": return nx.betweenness_centrality(g)
            elif method == "pagerank": return nx.pagerank(g)
            else: raise ValueError(f"Unknown method: {method}")

        # Offload CPU intensive task
        return await asyncio.to_thread(_compute, rels)

    async def find_subgraph_isomorphism(self, target_graph: nx.Graph, limit: int = 100) -> List[Dict[str, str]]:
        """Finds occurrences of a query graph (pattern). WARNING: Expensive."""
        client = self._require_client()

        query = """
        SELECT * FROM relationship
        WHERE (valid_to IS NONE OR valid_to > time::now())
        LIMIT $limit;
        """
        params = {"limit": limit}

        async with client.get_connection() as conn:
             response = await conn.query(query, params)
             rels = []
             if response and isinstance(response, list):
                  if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                      rels = response[0]['result']
                  else:
                      rels = response

        def _compute(rel_data):
            host_graph = nx.DiGraph()
            for r in rel_data:
                if isinstance(r, dict):
                    host_graph.add_edge(
                        r['from_entity_id'],
                        r['to_entity_id'],
                        relation_type=r.get('relation_type')
                    )

            gm = nx.algorithms.isomorphism.GraphMatcher(
                host_graph,
                target_graph,
                edge_match=nx.algorithms.isomorphism.categorical_edge_match('relation_type', None)
            )
            matches = []
            for i, subgraph in enumerate(gm.subgraph_isomorphisms_iter()):
                if i >= 5: break
                matches.append(subgraph)
            return matches

        return await asyncio.to_thread(_compute, rels)

    async def detect_communities(self, method: str = "louvain") -> Dict[str, List[str]]:
        """Detects communities. WARNING: In-memory processing."""
        client = self._require_client()

        query = """
        SELECT * FROM relationship
        WHERE (valid_to IS NONE OR valid_to > time::now())
        LIMIT 2000;
        """

        async with client.get_connection() as conn:
            response = await conn.query(query)
            rels = []
            if response and isinstance(response, list):
                 if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                     rels = response[0]['result']
                 else:
                     rels = response

        if not rels: return {}

        def _compute(rel_data):
            graph = nx.Graph()
            for r in rel_data:
                if isinstance(r, dict):
                    graph.add_edge(r['from_entity_id'], r['to_entity_id'], weight=r.get('strength', 1.0))

            communities = []
            try:
                if method == "louvain":
                    communities = nx.community.louvain_communities(graph, weight='weight')
                elif method == "girvan_newman":
                     comp = nx.community.girvan_newman(graph)
                     communities = next(comp)
                else:
                     communities = nx.community.greedy_modularity_communities(graph, weight='weight')
            except (AttributeError, ImportError):
                logger.warning("Advanced community detection not available, fallback to label propagation")
                communities = nx.community.label_propagation_communities(graph)

            result = {}
            for i, comm in enumerate(communities):
                result[f"community_{i}"] = list(comm)
            return result

        return await asyncio.to_thread(_compute, rels)

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
