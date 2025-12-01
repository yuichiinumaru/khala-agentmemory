import pytest
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.topic_detection_service import TopicDetectionService
from khala.application.services.pattern_recognition_service import PatternRecognitionService
from khala.application.services.prefetching_service import PredictivePrefetcher

@pytest.fixture
def mock_clients():
    gemini = MagicMock()
    gemini.generate_text = AsyncMock()

    db = MagicMock()
    db.get_user_sessions = AsyncMock()
    db.search_memories_by_bm25 = AsyncMock()

    return gemini, db

@pytest.mark.asyncio
async def test_cognitive_workflow(mock_clients):
    gemini, db = mock_clients

    # 1. Initialize Services
    topic_service = TopicDetectionService(gemini, db)
    pattern_service = PatternRecognitionService(gemini, db)
    prefetch_service = PredictivePrefetcher(gemini, db)

    # 2. Simulate User Interaction Loop
    user_id = "user_integration"
    query = "how to build agents"

    # --- Step A: Topic Detection ---
    db.get_user_sessions.return_value = [{"query": "python basics"}] # History
    gemini.generate_text.return_value = {
        "content": '{"changed": true, "current_topic": "Agents", "reason": "New subject"}'
    }

    topic_result = await topic_service.detect_topic_change(query, user_id)
    assert topic_result["changed"] is True

    # --- Step B: Pattern Recognition (Background) ---
    # Need at least 3 sessions for pattern recognition to trigger
    db.get_user_sessions.return_value = [
        {"timestamp": "2023-01-01", "query": "python"},
        {"timestamp": "2023-01-02", "query": "agents"},
        {"timestamp": "2023-01-03", "query": "memory"}
    ]
    gemini.generate_text.return_value = {
        "content": '[{"pattern_name": "AI Development", "confidence": 0.8}]'
    }
    patterns = await pattern_service.analyze_patterns(user_id)
    assert len(patterns) == 1
    assert patterns[0]["pattern_name"] == "AI Development"

    # --- Step C: Prefetching ---
    gemini.generate_text.return_value = {
        "content": '["agent frameworks", "memory systems"]'
    }
    db.search_memories_by_bm25.return_value = [{"id": "mem_agent_1"}]

    prefetch_result = await prefetch_service.prefetch_related_content(user_id, query, "learning")

    assert prefetch_result["prefetched_count"] > 0
    assert "agent frameworks" in prefetch_result["predicted_queries"]

    # Verify DB calls were made
    assert db.get_user_sessions.call_count >= 1 # Called by Topic & Pattern
    assert db.search_memories_by_bm25.call_count == 2 # 2 predictions
