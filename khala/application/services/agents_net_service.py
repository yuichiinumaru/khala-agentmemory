"""
Service for AgentsNet (Strategy 167): Network Topology Validation.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime
import networkx as nx

from khala.domain.agentsnet.entities import (
    NetworkTopology,
    TopologyType,
    ValidationResult,
    CoordinationMetrics,
    AgentNode,
    NetworkLink
)
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class AgentsNetService:
    """
    Service for managing and validating agent network topologies.
    Implements Strategy 167: Network Topology Validation.
    """

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def register_topology(self, topology: NetworkTopology) -> str:
        """
        Persists a network topology to the database.
        Returns the topology ID.
        """
        async with self.db_client.get_connection() as conn:
            # Parallelize insertions for better performance
            tasks = []
            for link in topology.links:
                task = conn.create("agent_network", {
                    "agent_1": link.agent_1,
                    "agent_2": link.agent_2,
                    "connection_strength": link.connection_strength,
                    "messages_exchanged": 0,
                    "coordination_success": False, # Initial state
                    "metadata": link.metadata,
                    "topology_id": topology.topology_id
                })
                tasks.append(task)

            if tasks:
                await asyncio.gather(*tasks)

        logger.info(f"Registered topology {topology.topology_id} with {len(topology.links)} links.")
        return topology.topology_id

    def validate_topology(self, topology: NetworkTopology) -> ValidationResult:
        """
        Validates the structural integrity of the network topology.
        Checks for connectivity, partitioning, and adherence to topology type rules.
        """
        issues = []
        is_valid = True

        # Build NetworkX graph for analysis
        G = nx.Graph()
        for node in topology.nodes:
            G.add_node(node.agent_id)
        for link in topology.links:
            G.add_edge(link.agent_1, link.agent_2, weight=link.connection_strength)

        num_nodes = G.number_of_nodes()

        # 1. Check Connectivity
        # Check size before is_connected to avoid NetworkXPointlessConcept error on null graph
        if num_nodes > 1:
            if not nx.is_connected(G):
                # Only strictly invalid for certain types, but generally a warning
                if topology.topology_type not in [TopologyType.RANDOM, TopologyType.CUSTOM]:
                     issues.append("Network is not fully connected (partitioned).")
                     is_valid = False # Strict for standard types

        # 2. Check specific topology rules
        if topology.topology_type == TopologyType.STAR:
            # Find center
            degrees = dict(G.degree())
            center_candidates = [n for n, d in degrees.items() if d == num_nodes - 1]
            if not center_candidates and num_nodes > 1:
                issues.append("Star topology requirement failed: No central node connected to all others.")
                is_valid = False

        elif topology.topology_type == TopologyType.RING:
            # Check if every node has degree 2
            degrees = dict(G.degree())
            if any(d != 2 for d in degrees.values()) and num_nodes > 2:
                 issues.append("Ring topology requirement failed: Not all nodes have degree 2.")
                 is_valid = False

        elif topology.topology_type == TopologyType.MESH:
             # Check for high connectivity (e.g. > 0.5 density) or full mesh
             density = nx.density(G)
             if density < 0.5: # Arbitrary threshold for "Mesh-like"
                 issues.append(f"Mesh topology density low ({density:.2f}).")
                 # Not necessarily invalid, just a warning

        # Calculate metrics safely
        diameter = -1
        if num_nodes > 1 and nx.is_connected(G):
            diameter = nx.diameter(G)

        avg_clustering = 0.0
        if num_nodes > 0:
            avg_clustering = nx.average_clustering(G)

        metrics = {
            "node_count": num_nodes,
            "edge_count": G.number_of_edges(),
            "density": nx.density(G),
            "diameter": diameter,
            "avg_clustering": avg_clustering
        }

        return ValidationResult(is_valid=is_valid, issues=issues, metrics=metrics)

    async def record_agent_state(self, agent_id: str, iteration: int, embedding: List[float], decision: str):
        """
        Records the state of an agent at a specific iteration (for Vector/TimeSeries analysis).
        """
        async with self.db_client.get_connection() as conn:
            await conn.create("agent_states", {
                "agent_id": agent_id,
                "iteration": iteration,
                "state_embedding": embedding,
                "decision_made": decision,
                "created_at": datetime.now().isoformat()
            })

    async def track_evolution(self, iteration: int, avg_coordination: float, message_count: int, topology_changes: int):
        """
        Records network evolution metrics (TimeSeries).
        """
        async with self.db_client.get_connection() as conn:
            await conn.create("network_evolution", {
                "iteration": iteration,
                "avg_coordination": avg_coordination,
                "message_count": message_count,
                "topology_changes": topology_changes,
                "created_at": datetime.now().isoformat()
            })

    async def simulate_network_step(self, topology_id: str) -> CoordinationMetrics:
        """
        Placeholder for running a simulation step on the network.
        In a real scenario, this would interact with the agents.
        """
        # Logic to fetch network, simulate message passing, and return metrics
        # For now, returns mock data
        return CoordinationMetrics(
            network_id=topology_id,
            iteration=1,
            avg_coordination_score=0.85,
            total_messages=120,
            successful_exchanges=115,
            failed_exchanges=5,
            topology_stability=1.0
        )
