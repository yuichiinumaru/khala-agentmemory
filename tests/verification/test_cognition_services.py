import pytest
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.topic_detection_service import TopicDetectionService
from khala.application.services.pattern_recognition_service import PatternRecognitionService

@pytest.fixture
def mock_gemini_client():
    client = MagicMock()
    client.generate_text = AsyncMock()
    return client

@pytest.fixture
def mock_db_client():
    client = MagicMock()
    client.get_user_sessions = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_topic_detection_no_history(mock_gemini_client, mock_db_client):
    service = TopicDetectionService(mock_gemini_client, mock_db_client)
    mock_db_client.get_user_sessions.return_value = []

    result = await service.detect_topic_change("new query", "user1")

    assert result["changed"] is True
    assert result["reason"] == "No previous history found."

@pytest.mark.asyncio
async def test_topic_detection_change(mock_gemini_client, mock_db_client):
    service = TopicDetectionService(mock_gemini_client, mock_db_client)
    mock_db_client.get_user_sessions.return_value = [
        {"query": "cats"}, {"query": "dogs"}
    ]

    # Mock LLM response
    mock_gemini_client.generate_text.return_value = {
        "content": '```json\n{"changed": true, "previous_topic": "Pets", "current_topic": "Cars", "reason": "Shift from animals to vehicles"}\n```'
    }

    result = await service.detect_topic_change("ferrari", "user1")

    assert result["changed"] is True
    assert result["current_topic"] == "Cars"
    mock_gemini_client.generate_text.assert_called_once()

@pytest.mark.asyncio
async def test_pattern_recognition(mock_gemini_client, mock_db_client):
    service = PatternRecognitionService(mock_gemini_client, mock_db_client)
    mock_db_client.get_user_sessions.return_value = [
        {"timestamp": "2023-01-01", "query": "python details"},
        {"timestamp": "2023-01-02", "query": "python async"},
        {"timestamp": "2023-01-03", "query": "python testing"}
    ]

    mock_gemini_client.generate_text.return_value = {
        "content": '```json\n[{"pattern_name": "Python Learning", "confidence": 0.9}]\n```'
    }

    result = await service.analyze_patterns("user1")

    assert len(result) == 1
    assert result[0]["pattern_name"] == "Python Learning"
