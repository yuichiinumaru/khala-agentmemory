import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone, timedelta

from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore, Relationship, Entity, EntityType
from khala.infrastructure.persistence.surrealdb_repository import SurrealDBMemoryRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.audit.entities import AuditLog
from khala.infrastructure.persistence.audit_repository import AuditRepository
from khala.domain.graph.service import GraphService
from khala.infrastructure.coordination.distributed_lock import SurrealDBLock

@pytest.fixture
def mock_client():
    client = MagicMock(spec=SurrealDBClient)
    client.create_memory = AsyncMock(return_value="mem1")
    client.update_memory = AsyncMock()
    client.delete_memory = AsyncMock()
    client.get_connection = MagicMock()
    client.create_entity = AsyncMock(return_value="ent1")
    client.create_relationship = AsyncMock(return_value="rel1")
    return client

@pytest.fixture
def mock_audit_repo():
    repo = MagicMock(spec=AuditRepository)
    repo.log = AsyncMock()
    return repo

@pytest.mark.asyncio
async def test_audit_logging(mock_client, mock_audit_repo):
    repo = SurrealDBMemoryRepository(mock_client, mock_audit_repo)
    memory = Memory(
        user_id="user1",
        content="test",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5)
    )

    await repo.create(memory)

    mock_audit_repo.log.assert_called_once()
    call_args = mock_audit_repo.log.call_args[0][0]
    assert isinstance(call_args, AuditLog)
    assert call_args.action == "create"
    assert call_args.target_type == "memory"

@pytest.mark.asyncio
async def test_bitemporal_relationship():
    rel = Relationship(
        from_entity_id="a",
        to_entity_id="b",
        relation_type="friend",
        strength=0.8,
        transaction_time_start=datetime.now(timezone.utc)
    )
    assert rel.transaction_time_start is not None
    assert rel.transaction_time_end is None

    # Test validation
    with pytest.raises(ValueError):
        Relationship(
            from_entity_id="a",
            to_entity_id="b",
            relation_type="x",
            strength=0.1,
            transaction_time_end=datetime(2000, 1, 1, tzinfo=timezone.utc),
            transaction_time_start=datetime(2020, 1, 1, tzinfo=timezone.utc)
        )

@pytest.mark.asyncio
async def test_hyperedge_creation(mock_client):
    repo = SurrealDBMemoryRepository(mock_client)
    repo.client = mock_client

    service = GraphService(repo)

    entities = ["e1", "e2", "e3"]
    hyper_id = await service.create_hyperedge(entities, "MEETING")

    mock_client.create_entity.assert_called_once()
    assert mock_client.create_relationship.call_count == 3
    assert hyper_id is not None

@pytest.mark.asyncio
async def test_distributed_lock_acquire(mock_client):
    lock = SurrealDBLock(mock_client, "test_lock")

    # Mock context manager for get_connection
    conn_mock = AsyncMock()
    # Mock query response
    conn_mock.query.return_value = []

    mock_client.get_connection.return_value.__aenter__.return_value = conn_mock

    result = await lock.acquire()
    assert result is True

    # Verify cleanup was called
    assert "DELETE lock WHERE id = $id AND expires_at < time::now();" in str(conn_mock.query.call_args_list[0])

@pytest.mark.asyncio
async def test_inherited_relationships(mock_client):
    repo = SurrealDBMemoryRepository(mock_client)
    repo.client = mock_client
    service = GraphService(repo)

    # Mock responses for get_inherited_relationships
    conn_mock = AsyncMock()
    mock_client.get_connection.return_value.__aenter__.return_value = conn_mock

    # 1. Direct relationships query
    # 2. Parent query
    # 3. Parent relationships query

    def side_effect(query, params):
        if "WHERE from_entity_id = $id;" in query and params['id'] == "child":
            return [{"result": [], "status": "OK"}] # No direct

        if "(relation_type = 'is_a' OR relation_type = 'subclass_of')" in query:
             return [{"result": [{"to_entity_id": "parent"}], "status": "OK"}]

        if "WHERE from_entity_id = $id;" in query and params['id'] == "parent":
             return [{"result": [{
                 "id": "rel1",
                 "from_entity_id": "parent",
                 "to_entity_id": "uncle",
                 "relation_type": "friend",
                 "strength": 0.5,
                 "valid_from": datetime.now(timezone.utc).isoformat(),
                 "transaction_time_start": datetime.now(timezone.utc).isoformat()
             }], "status": "OK"}]

        return []

    conn_mock.query.side_effect = side_effect

    rels = await service.get_inherited_relationships("child")

    assert len(rels) == 1
    assert rels[0].from_entity_id == "child"
    assert rels[0].to_entity_id == "uncle"
