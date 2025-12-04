import pytest
from unittest.mock import AsyncMock, MagicMock
from khala.application.services.approval_service import ApprovalService
from khala.application.services.surprise_service import SurpriseService
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.domain.memory.entities import Memory, ImportanceScore

@pytest.fixture
def mock_db_client():
    client = MagicMock(spec=SurrealDBClient)
    client.get_connection = MagicMock()
    mock_conn = AsyncMock()
    client.get_connection.return_value.__aenter__.return_value = mock_conn
    client.get_connection.return_value.__aexit__.return_value = None
    client.create = AsyncMock(return_value={"id": "req:1"})
    return client

@pytest.fixture
def mock_gemini():
    client = MagicMock(spec=GeminiClient)
    # Mocking classification response
    client.generate_text = AsyncMock(return_value={"content": "0.8"})
    return client

@pytest.mark.asyncio
@pytest.mark.strategy(125)
async def test_approval_flow(mock_db_client):
    service = ApprovalService(mock_db_client)

    # 1. Request
    req_id = await service.request_approval("delete", "mem:1", "user:1", "Delete memory")
    assert req_id.startswith("approval_request:")

    # 2. Get Pending
    mock_conn = mock_db_client.get_connection.return_value.__aenter__.return_value
    mock_conn.query.return_value = [{"result": [{"id": "req:1", "status": "pending"}]}]

    pending = await service.get_pending_approvals()
    assert len(pending) == 1

    # 3. Approve
    await service.approve("req:1", "admin:1")

    # Verify update query
    args, _ = mock_conn.query.call_args
    assert "UPDATE type::thing('approval_request', $id)" in args[0]
    assert args[1]["status"] == "approved"

@pytest.mark.asyncio
@pytest.mark.strategy(133)
async def test_surprise_detection(mock_gemini):
    service = SurpriseService(mock_gemini)

    score = await service.detect_surprise("Aliens landed", "Sky is blue")
    assert score == 0.8

    mem = Memory(id="m1", user_id="u1", content="Aliens", tier="working", importance=ImportanceScore(0.5))
    context_mems = [Memory(id="m2", user_id="u1", content="Normal day", tier="working", importance=ImportanceScore(0.5))]

    await service.process_memory_surprise(mem, context_mems)

    assert mem.importance.value == 1.0
    assert mem.metadata["surprise_detected"] is True
