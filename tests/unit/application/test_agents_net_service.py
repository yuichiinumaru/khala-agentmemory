"""
Unit tests for AgentsNetService.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, ANY
from khala.application.services.agents_net_service import AgentsNetService
from khala.domain.agentsnet.entities import (
    NetworkTopology,
    AgentNode,
    NetworkLink,
    TopologyType
)
from khala.infrastructure.surrealdb.client import SurrealDBClient

@pytest.fixture
def mock_db_connection():
    # Mock the connection object returned by get_connection context manager
    conn = AsyncMock()
    conn.create = AsyncMock()
    return conn

@pytest.fixture
def mock_db_client(mock_db_connection):
    client = AsyncMock(spec=SurrealDBClient)
    # Mock the context manager
    client.get_connection.return_value.__aenter__.return_value = mock_db_connection
    client.get_connection.return_value.__aexit__.return_value = None
    return client

@pytest.fixture
def service(mock_db_client):
    return AgentsNetService(mock_db_client)

@pytest.mark.asyncio
async def test_register_topology(service, mock_db_connection):
    node1 = AgentNode(agent_id="agent1")
    node2 = AgentNode(agent_id="agent2")
    link = NetworkLink(agent_1="agent1", agent_2="agent2")
    topology = NetworkTopology(
        topology_id="topo1",
        topology_type=TopologyType.MESH,
        nodes=[node1, node2],
        links=[link]
    )

    result = await service.register_topology(topology)

    assert result == "topo1"
    mock_db_connection.create.assert_called()
    assert mock_db_connection.create.call_count == 1

    # Verify call args
    args = mock_db_connection.create.call_args[0]
    assert args[0] == "agent_network"
    assert args[1]["agent_1"] == "agent1"
    assert args[1]["agent_2"] == "agent2"

def test_validate_topology_star_valid(service):
    # Center + 3 leaves
    center = AgentNode(agent_id="center")
    leaves = [AgentNode(agent_id=f"leaf{i}") for i in range(3)]
    nodes = [center] + leaves
    links = [NetworkLink(agent_1="center", agent_2=l.agent_id) for l in leaves]

    topology = NetworkTopology(
        topology_id="star1",
        topology_type=TopologyType.STAR,
        nodes=nodes,
        links=links
    )

    result = service.validate_topology(topology)
    assert result.is_valid is True
    assert result.metrics["node_count"] == 4
    assert result.metrics["edge_count"] == 3

def test_validate_topology_star_invalid(service):
    # Disconnected graph disguised as STAR
    nodes = [AgentNode(agent_id="a"), AgentNode(agent_id="b"), AgentNode(agent_id="c")]
    links = [NetworkLink(agent_1="a", agent_2="b")] # c is disconnected

    topology = NetworkTopology(
        topology_id="star_fail",
        topology_type=TopologyType.STAR,
        nodes=nodes,
        links=links
    )

    result = service.validate_topology(topology)
    assert result.is_valid is False
    assert any("not fully connected" in i for i in result.issues)

def test_validate_topology_ring_valid(service):
    # A-B-C-A
    nodes = [AgentNode(agent_id="a"), AgentNode(agent_id="b"), AgentNode(agent_id="c")]
    links = [
        NetworkLink(agent_1="a", agent_2="b"),
        NetworkLink(agent_1="b", agent_2="c"),
        NetworkLink(agent_1="c", agent_2="a")
    ]

    topology = NetworkTopology(
        topology_id="ring1",
        topology_type=TopologyType.RING,
        nodes=nodes,
        links=links
    )

    result = service.validate_topology(topology)
    assert result.is_valid is True

def test_validate_topology_empty(service):
    # Empty topology should not crash
    topology = NetworkTopology(
        topology_id="empty",
        topology_type=TopologyType.MESH,
        nodes=[],
        links=[]
    )

    result = service.validate_topology(topology)
    assert result.is_valid is True # Empty might be considered valid or trivially valid
    assert result.metrics["node_count"] == 0

def test_validate_topology_single_node(service):
    # Single node topology should not crash
    topology = NetworkTopology(
        topology_id="single",
        topology_type=TopologyType.MESH,
        nodes=[AgentNode(agent_id="a")],
        links=[]
    )

    result = service.validate_topology(topology)
    assert result.is_valid is True
    assert result.metrics["node_count"] == 1
    assert result.metrics["diameter"] == -1 # Or 0 depending on logic, but not crash

@pytest.mark.asyncio
async def test_record_agent_state(service, mock_db_connection):
    await service.record_agent_state("agent1", 1, [0.1, 0.2], "action_a")

    mock_db_connection.create.assert_called_with(
        "agent_states",
        {
            "agent_id": "agent1",
            "iteration": 1,
            "state_embedding": [0.1, 0.2],
            "decision_made": "action_a",
            "created_at":  ANY
        }
    )

@pytest.mark.asyncio
async def test_track_evolution(service, mock_db_connection):
    await service.track_evolution(1, 0.9, 100, 2)

    mock_db_connection.create.assert_called_with(
        "network_evolution",
        {
            "iteration": 1,
            "avg_coordination": 0.9,
            "message_count": 100,
            "topology_changes": 2,
            "created_at": ANY
        }
    )
