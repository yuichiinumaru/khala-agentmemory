"""Unit tests for Quality Analytics Service (Tasks 107 & 108)."""

import pytest
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone, timedelta

from khala.application.analytics.quality_metrics import QualityAnalyticsService
from khala.infrastructure.surrealdb.client import SurrealDBClient

@pytest.fixture
def mock_db_client():
    client = MagicMock(spec=SurrealDBClient)
    client.get_connection = MagicMock()
    return client

@pytest.mark.asyncio
async def test_get_debate_trends_empty(mock_db_client):
    """Test debate trends with no data."""
    service = QualityAnalyticsService(mock_db_client)

    # Mock empty result
    mock_conn = AsyncMock()
    mock_conn.query.return_value = []
    mock_db_client.get_connection.return_value.__aenter__.return_value = mock_conn

    trends = await service.get_debate_trends()

    assert trends["total_debates"] == 0
    assert trends["trends"] == []

@pytest.mark.asyncio
async def test_get_debate_trends_data(mock_db_client):
    """Test debate trends with data."""
    service = QualityAnalyticsService(mock_db_client)

    # Mock data
    mock_data = [
        {
            "created_at": "2023-10-01T10:00:00Z",
            "score": 0.8,
            "decision": "ACCEPTED",
            "confidence": 0.9
        },
        {
            "created_at": "2023-10-01T12:00:00Z",
            "score": 0.6,
            "decision": "REFINE_REQUESTED",
            "confidence": 0.5
        },
        {
            "created_at": "2023-10-02T10:00:00Z",
            "score": 0.9,
            "decision": "ACCEPTED",
            "confidence": 0.95
        }
    ]

    mock_conn = AsyncMock()
    # SurrealDB returns [{"result": [...]}] usually, handling both formats in code
    mock_conn.query.return_value = [{"result": mock_data}]
    mock_db_client.get_connection.return_value.__aenter__.return_value = mock_conn

    trends = await service.get_debate_trends()

    assert trends["total_debates"] == 3
    assert len(trends["trends"]) == 2  # 2 days

    day1 = trends["trends"][0]
    assert day1["date"] == "2023-10-01"
    assert day1["debates_count"] == 2
    assert day1["avg_consensus_score"] == 0.7
    assert day1["decisions_breakdown"]["ACCEPTED"] == 1
    assert day1["decisions_breakdown"]["REFINE_REQUESTED"] == 1

    day2 = trends["trends"][1]
    assert day2["date"] == "2023-10-02"
    assert day2["debates_count"] == 1
    assert day2["avg_consensus_score"] == 0.9

@pytest.mark.asyncio
async def test_get_learning_curve(mock_db_client):
    """Test learning curve generation."""
    service = QualityAnalyticsService(mock_db_client)

    mock_data = [
        {"created_at": "2023-10-01T10:00:00Z", "verification_score": 0.5},
        {"created_at": "2023-10-02T10:00:00Z", "verification_score": 0.6},
        {"created_at": "2023-10-03T10:00:00Z", "verification_score": 0.7},
        {"created_at": "2023-10-03T12:00:00Z", "verification_score": 0.9}
    ]

    mock_conn = AsyncMock()
    mock_conn.query.return_value = [{"result": mock_data}]
    mock_db_client.get_connection.return_value.__aenter__.return_value = mock_conn

    curve = await service.get_learning_curve()

    assert curve["data_points"] == 4
    assert len(curve["curve"]) == 3 # 3 days

    # Day 1
    assert curve["curve"][0]["date"] == "2023-10-01"
    assert curve["curve"][0]["daily_avg_score"] == 0.5
    assert curve["curve"][0]["running_avg_score"] == 0.5

    # Day 2
    assert curve["curve"][1]["date"] == "2023-10-02"
    assert curve["curve"][1]["daily_avg_score"] == 0.6
    assert curve["curve"][1]["running_avg_score"] == 0.55  # (0.5 + 0.6) / 2

    # Day 3
    assert curve["curve"][2]["date"] == "2023-10-03"
    assert curve["curve"][2]["daily_avg_score"] == 0.8  # (0.7 + 0.9) / 2
    assert curve["curve"][2]["running_avg_score"] == 0.675  # (0.5 + 0.6 + 0.7 + 0.9) / 4
