import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, Mock, MagicMock
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.application.services.hybrid_search_service import HybridSearchService
from khala.domain.memory.entities import Memory, EmbeddingVector
from khala.domain.memory.value_objects import MemoryTier, ImportanceScore
from khala.domain.graph.service import GraphService
from khala.domain.memory.repository import MemoryRepository

# --- Mocks ---

@pytest.fixture
def mock_db_client():
    client = MagicMock(spec=SurrealDBClient)
    client.get_connection = MagicMock()
    # Mock the context manager for get_connection
    mock_conn = AsyncMock()
    client.get_connection.return_value.__aenter__.return_value = mock_conn
    client.get_connection.return_value.__aexit__.return_value = None
    return client

@pytest.fixture
def mock_repo(mock_db_client):
    repo = MagicMock(spec=MemoryRepository)
    repo.client = mock_db_client
    return repo

@pytest.fixture
def mock_embedding_service():
    service = AsyncMock()
    service.get_embedding.return_value = [0.1] * 768
    return service

# --- Tests for Strategy 67 (Bi-temporal) ---

@pytest.mark.asyncio
async def test_archive_relationship(mock_db_client):
    """Test soft deletion of relationship."""
    # Setup
    mock_conn = mock_db_client.get_connection.return_value.__aenter__.return_value

    # Act
    # We are testing the client method, so we need to instantiate a real client with mocked connection logic
    # But since we mocked the whole client in fixture, we can just test the logic if we had a real client
    # OR we can just unit test the method by monkeypatching.
    # Let's verify the query structure by invoking the method on the class if possible,
    # but since it's an instance method, let's copy the method logic or trust the client logic is simple.

    # Actually, we should test the client method itself.
    client = SurrealDBClient(url="ws://test", username="user", password="pass")
    client.get_connection = MagicMock()
    mock_conn_real = AsyncMock()
    client.get_connection.return_value.__aenter__.return_value = mock_conn_real
    client.get_connection.return_value.__aexit__.return_value = None

    await client.archive_relationship("rel:123")

    # Verify query
    mock_conn_real.query.assert_called_once()
    args, _ = mock_conn_real.query.call_args
    assert "UPDATE type::thing('relationship', $id)" in args[0]
    assert "SET valid_to = time::now()" in args[0]
    assert args[1]["id"] == "123"

@pytest.mark.asyncio
async def test_get_relationships_at_time(mock_db_client):
    """Test time travel query."""
    client = SurrealDBClient(url="ws://test", username="user", password="pass")
    client.get_connection = MagicMock()
    mock_conn_real = AsyncMock()
    client.get_connection.return_value.__aenter__.return_value = mock_conn_real
    client.get_connection.return_value.__aexit__.return_value = None

    ts = datetime(2023, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    await client.get_relationships_at_time("entity:abc", ts)

    mock_conn_real.query.assert_called_once()
    args, _ = mock_conn_real.query.call_args
    assert "valid_from <= $timestamp" in args[0]
    assert args[1]["entity_id"] == "abc"
    assert args[1]["timestamp"] == ts.isoformat()

# --- Tests for Strategy 121 (Graph Reranking) ---

@pytest.mark.asyncio
async def test_hybrid_search_graph_reranking(mock_repo, mock_embedding_service, mock_db_client):
    """Test that search boosts results based on graph connections."""
    service = HybridSearchService(
        memory_repository=mock_repo,
        embedding_service=mock_embedding_service,
        db_client=mock_db_client
    )

    # Create candidates
    # Memory A: Anchor (Top score initially)
    mem_a = Memory(id="A", user_id="u1", content="A", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5), episode_id="ep1")
    # Memory B: Connected to A via graph
    mem_b = Memory(id="B", user_id="u1", content="B", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5), episode_id="ep2")
    # Memory C: Same episode as A
    mem_c = Memory(id="C", user_id="u1", content="C", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5), episode_id="ep1")
    # Memory D: Unrelated
    mem_d = Memory(id="D", user_id="u1", content="D", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5), episode_id="ep3")

    # Setup repo to return these (simulating vector/bm25 return)
    mock_repo.search_by_vector.return_value = [mem_a, mem_b, mem_c, mem_d]
    mock_repo.search_by_text.return_value = []

    # Setup Graph DB response for anchor A
    # Return B as a connection
    mock_conn = mock_db_client.get_connection.return_value.__aenter__.return_value
    mock_conn.query.return_value = [{"result": [{"from_entity_id": "A", "to_entity_id": "B"}]}]

    # Act
    results = await service.search(
        query="test",
        user_id="u1",
        enable_graph_reranking=True
    )

    # Assert
    # Logic:
    # A is #0.
    # C gets +0.15 boost (Same Episode)
    # B gets +0.10 boost (Graph Neighbor)
    # D gets +0.00 boost
    #
    # Original RRF:
    # A: 1/(60+1) = 0.01639
    # B: 1/(60+2) = 0.01612
    # C: 1/(60+3) = 0.01587
    # D: 1/(60+4) = 0.01562
    #
    # Boosted Sorting (Stable desc by boost):
    # C: 0.15
    # B: 0.10
    # A: 0.00 (But it was anchor, does it get boosted? No logic says if m.episode == anchor.episode. A.episode == A.episode so YES A gets 0.15 too!)
    # Wait, check logic: `if anchor_episode and m.episode_id == anchor_episode:`
    # A matches A. So A gets +0.15.
    # C matches A. So C gets +0.15.
    # B is neighbor. Gets +0.10.
    # D is nothing.
    #
    # Sort order (Boost desc, Original Index asc):
    # 1. A (Boost 0.15, Idx 0)
    # 2. C (Boost 0.15, Idx 2)
    # 3. B (Boost 0.10, Idx 1) -> Wait, B was idx 1.
    # 4. D (Boost 0.0, Idx 3)

    assert results[0].id == "A"
    assert results[1].id == "C" # C should jump over B
    assert results[2].id == "B"
    assert results[3].id == "D"

# --- Tests for Strategy 71 (Recursive Graph) ---

@pytest.mark.asyncio
async def test_get_entity_descendants(mock_repo):
    """Test recursive traversal call."""
    service = GraphService(repository=mock_repo)
    mock_conn = mock_repo.client.get_connection.return_value.__aenter__.return_value

    await service.get_entity_descendants("ent1")

    mock_conn.query.assert_called_once()
    args, _ = mock_conn.query.call_args
    assert "fn::get_descendants" in args[0]
    assert args[1]["start_node"] == "ent1"
