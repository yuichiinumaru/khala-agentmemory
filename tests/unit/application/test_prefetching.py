import pytest
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.prefetching_service import PredictivePrefetcher

@pytest.fixture
def mock_gemini_client():
    client = MagicMock()
    client.generate_text = AsyncMock()
    return client

@pytest.fixture
def mock_db_client():
    client = MagicMock()
    client.search_memories_by_bm25 = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_prefetching_flow(mock_gemini_client, mock_db_client):
    service = PredictivePrefetcher(mock_gemini_client, mock_db_client)

    # Mock Prediction
    mock_gemini_client.generate_text.return_value = {
        "content": '["next query 1", "next query 2"]'
    }

    # Mock DB Search
    mock_db_client.search_memories_by_bm25.return_value = [{"id": "mem1"}, {"id": "mem2"}]

    result = await service.prefetch_related_content(
        user_id="user1",
        current_query="current query",
        current_intent="informational"
    )

    assert "predicted_queries" in result
    assert len(result["predicted_queries"]) == 2
    assert result["prefetched_count"] == 4 # 2 queries * 2 results each
    assert mock_db_client.search_memories_by_bm25.call_count == 2

@pytest.mark.asyncio
async def test_prefetching_empty_prediction(mock_gemini_client, mock_db_client):
    service = PredictivePrefetcher(mock_gemini_client, mock_db_client)

    mock_gemini_client.generate_text.return_value = {
        "content": '[]'
    }

    result = await service.prefetch_related_content("user1", "q", "i")

    assert result["prefetched_count"] == 0
    mock_db_client.search_memories_by_bm25.assert_not_called()
