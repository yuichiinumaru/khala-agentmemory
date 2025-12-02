import pytest
from unittest.mock import AsyncMock, MagicMock
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.application.services.anchor_point_service import AnchorPointService
from khala.application.services.bias_detection_service import BiasDetectionService

@pytest.fixture
def mock_db_client():
    client = MagicMock(spec=SurrealDBClient)
    client.get_connection = MagicMock()
    mock_conn = AsyncMock()
    client.get_connection.return_value.__aenter__.return_value = mock_conn
    client.get_connection.return_value.__aexit__.return_value = None
    return client

@pytest.fixture
def mock_gemini_client():
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_identify_anchors(mock_db_client):
    service = AnchorPointService(mock_db_client)
    mock_conn = mock_db_client.get_connection.return_value.__aenter__.return_value

    # Mock return of UPDATE query
    mock_conn.query.return_value = [{"id": "m1"}, {"id": "m2"}]

    count = await service.identify_anchors("u1", 0.9, 10)

    assert count == 2
    mock_conn.query.assert_called_once()
    args, _ = mock_conn.query.call_args
    assert "UPDATE memory" in args[0]
    assert args[1]["threshold"] == 0.9
    assert args[1]["min_access"] == 10

@pytest.mark.asyncio
async def test_get_anchors(mock_db_client):
    service = AnchorPointService(mock_db_client)
    mock_conn = mock_db_client.get_connection.return_value.__aenter__.return_value

    mock_conn.query.return_value = [
        {"id": "m1", "is_anchor": True, "content": "A"},
        {"id": "m2", "is_anchor": True, "content": "B"}
    ]

    anchors = await service.get_anchors("u1")

    assert len(anchors) == 2
    assert anchors[0]["id"] == "m1"

@pytest.mark.asyncio
async def test_analyze_memory_bias(mock_db_client, mock_gemini_client):
    service = BiasDetectionService(mock_gemini_client, mock_db_client)
    mock_conn = mock_db_client.get_connection.return_value.__aenter__.return_value

    # Mock memory fetch and then update
    mock_conn.query.side_effect = [
        # First query: SELECT * FROM memory
        [{"id": "m1", "content": "Biased content"}],
        # Second query: UPDATE memory
        None
    ]

    # Mock LLM response
    mock_gemini_client.generate_text.return_value = {
        "content": '```json\n{"bias_score": 0.8, "bias_analysis": "Biased", "detected_biases": ["bias1"]}\n```'
    }

    result = await service.analyze_memory_bias("m1")

    assert result["bias_score"] == 0.8
    assert result["bias_analysis"] == "Biased"

    # Verify update called
    assert mock_conn.query.call_count == 2
    args, _ = mock_conn.query.call_args
    assert "UPDATE memory" in args[0]
    assert args[1]["score"] == 0.8

@pytest.mark.asyncio
async def test_analyze_sentiment_distribution(mock_db_client, mock_gemini_client):
    service = BiasDetectionService(mock_gemini_client, mock_db_client)
    mock_conn = mock_db_client.get_connection.return_value.__aenter__.return_value

    # Mock aggregation query result
    mock_conn.query.return_value = [
        {"count": 10, "label": "positive", "avg_score": 0.8},
        {"count": 5, "label": "negative", "avg_score": -0.5}
    ]

    result = await service.analyze_sentiment_distribution("u1")

    assert result["total_memories_with_sentiment"] == 15
    assert result["distribution"]["positive"]["percentage"] == 66.67
    assert result["distribution"]["negative"]["percentage"] == 33.33
