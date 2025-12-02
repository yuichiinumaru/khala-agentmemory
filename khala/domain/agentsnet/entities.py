"""
Domain entities for AgentsNet (Strategy 167): Network Topology Validation.
"""

from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime

class TopologyType(str, Enum):
    MESH = "mesh"
    STAR = "star"
    RING = "ring"
    RANDOM = "random"
    CUSTOM = "custom"
    HIERARCHICAL = "hierarchical"

class AgentNode(BaseModel):
    """Represents an agent in the network."""
    agent_id: str
    role: Optional[str] = None
    capabilities: List[str] = Field(default_factory=list)
    state_embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class NetworkLink(BaseModel):
    """Represents a connection between two agents."""
    agent_1: str
    agent_2: str
    connection_strength: float = 1.0
    link_type: str = "direct"
    metadata: Dict[str, Any] = Field(default_factory=dict)

class NetworkTopology(BaseModel):
    """Represents the entire agent network structure."""
    topology_id: str
    topology_type: TopologyType
    nodes: List[AgentNode] = Field(default_factory=list)
    links: List[NetworkLink] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    def add_node(self, node: AgentNode):
        if not any(n.agent_id == node.agent_id for n in self.nodes):
            self.nodes.append(node)

    def add_link(self, link: NetworkLink):
        # Validate that agents exist in the network
        agent_ids = {n.agent_id for n in self.nodes}
        if link.agent_1 in agent_ids and link.agent_2 in agent_ids:
             self.links.append(link)
        else:
            raise ValueError(f"One or both agents ({link.agent_1}, {link.agent_2}) not found in network nodes.")

class CoordinationMetrics(BaseModel):
    """Metrics for measuring coordination success."""
    network_id: str
    iteration: int
    avg_coordination_score: float
    total_messages: int
    successful_exchanges: int
    failed_exchanges: int
    topology_stability: float
    timestamp: datetime = Field(default_factory=datetime.now)

class ValidationResult(BaseModel):
    """Result of a topology validation check."""
    is_valid: bool
    issues: List[str] = Field(default_factory=list)
    metrics: Dict[str, Any] = Field(default_factory=dict)
