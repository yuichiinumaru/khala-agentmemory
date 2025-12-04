import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.graph_cache_service import GraphCacheService
from datetime import datetime, timezone

@pytest.fixture
def mock_client():
    client = MagicMock()
    client.get_cache_entry = AsyncMock()
    client.create_cache_entry = AsyncMock()
    client.update_cache_entry = AsyncMock()
    return client

def test_cache_miss(mock_client):
    asyncio.run(_test_cache_miss(mock_client))

async def _test_cache_miss(mock_client):
    service = GraphCacheService(mock_client)
    mock_client.get_cache_entry.return_value = None

    path = await service.get_cached_path("A", "B")
    assert path is None

def test_cache_hit(mock_client):
    asyncio.run(_test_cache_hit(mock_client))

async def _test_cache_hit(mock_client):
    service = GraphCacheService(mock_client)
    entry = {
        "value": {"path": [{"id": "A"}, {"id": "B"}]},
        "expires_at": "2099-01-01T00:00:00Z"
    }
    mock_client.get_cache_entry.return_value = entry

    path = await service.get_cached_path("A", "B")
    assert len(path) == 2
    mock_client.update_cache_entry.assert_called_once()
