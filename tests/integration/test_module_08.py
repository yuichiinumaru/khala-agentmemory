import pytest
from unittest.mock import AsyncMock, MagicMock
from khala.application.services.query_expansion_service import QueryExpansionService
from khala.application.services.topic_detection_service import TopicDetectionService
from khala.application.services.pattern_recognition_service import PatternRecognitionService
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient

@pytest.fixture
def mock_gemini_client():
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock()
    return client

@pytest.fixture
def mock_db_client():
    client = MagicMock(spec=SurrealDBClient)
    client.get_user_sessions = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_query_expansion(mock_gemini_client):
    service = QueryExpansionService(mock_gemini_client)
    mock_gemini_client.generate_text.return_value = {
        "content": "python async\npython concurrency\npython await"
    }

    results = await service.expand_query("python async", num_expansions=3)

    assert "python async" in results # Original query should be there
    assert "python concurrency" in results
    assert len(results) > 1

@pytest.mark.asyncio
async def test_topic_detection_change(mock_gemini_client, mock_db_client):
    service = TopicDetectionService(mock_gemini_client, mock_db_client)

    # Mock history
    mock_db_client.get_user_sessions.return_value = [
        {"query": "best pizza recipe", "timestamp": "2023-01-01T10:00:00Z"}
    ]

    # Mock LLM response for change
    mock_gemini_client.generate_text.return_value = {
        "content": '{"changed": true, "previous_topic": "cooking", "current_topic": "politics", "reason": "different domain"}'
    }

    result = await service.detect_topic_change("who is the president", "user123")

    assert result["changed"] is True
    assert result["previous_topic"] == "cooking"

@pytest.mark.asyncio
async def test_pattern_recognition(mock_gemini_client, mock_db_client):
    service = PatternRecognitionService(mock_gemini_client, mock_db_client)

    # Mock sessions
    mock_db_client.get_user_sessions.return_value = [
        {"query": "q1", "timestamp": "t1"},
        {"query": "q2", "timestamp": "t2"},
        {"query": "q3", "timestamp": "t3"}
    ]

    # Mock LLM response
    mock_gemini_client.generate_text.return_value = {
        "content": '[{"pattern_name": "coding", "confidence": 0.9}]'
    }

    patterns = await service.analyze_patterns("user123")

    assert len(patterns) == 1
    assert patterns[0]["pattern_name"] == "coding"
