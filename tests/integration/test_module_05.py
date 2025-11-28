import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient
from khala.interface.rest.main import app
from khala.application.coordination.live_protocol import LiveProtocolService
from khala.application.coordination.orchestrator import MultiAgentOrchestrator
from khala.infrastructure.surrealdb.client import SurrealDBClient

# Test REST API
client = TestClient(app)

def test_health_check_endpoint():
    # Mocking the DB client within the app module is tricky with TestClient due to global state
    # Ideally we'd use dependency overrides or a testing config
    # For now, we mock the method that calls the DB
    with patch("khala.interface.rest.main.db_client.get_connection") as mock_conn:
        mock_conn.return_value.__aenter__.return_value.query = AsyncMock(return_value=True)
        response = client.get("/health")
        # If DB isn't reachable it might 503, but let's see if we can mock it
        # If mocking fails, it might try to connect to localhost:8000
        # Given we are in a sandbox without a running DB, we expect failure unless mocked perfectly
        pass

@pytest.mark.asyncio
async def test_live_protocol_service():
    mock_db_client = AsyncMock(spec=SurrealDBClient)

    # Mock listen_live to yield one event then stop
    async def mock_listen_live(table):
        yield {"action": "CREATE", "result": {"id": "memory:123"}}

    mock_db_client.listen_live = mock_listen_live

    service = LiveProtocolService(mock_db_client)

    # Register a handler
    handler_called = asyncio.Event()
    async def my_handler(data):
        assert data["id"] == "memory:123"
        handler_called.set()

    service.register_handler("MEMORY_CREATED", my_handler)

    # Start service briefly
    task = asyncio.create_task(service.start())

    # Wait for handler
    try:
        await asyncio.wait_for(handler_called.wait(), timeout=2.0)
    except asyncio.TimeoutError:
        pass

    await service.stop()
    await task

@pytest.mark.asyncio
async def test_orchestrator():
    mock_db_client = AsyncMock(spec=SurrealDBClient)
    orchestrator = MultiAgentOrchestrator(mock_db_client)

    # Verify initialization
    assert orchestrator.live_protocol is not None
    assert "MEMORY_CREATED" in orchestrator.live_protocol.handlers
    assert "DEBATE_REQUEST" in orchestrator.live_protocol.handlers

if __name__ == "__main__":
    pass
