import pytest
from unittest.mock import AsyncMock, MagicMock
from khala.application.services.dr_mamr_service import DrMAMRService, DrMAMRTrace
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient

@pytest.fixture
def mock_gemini_client():
    client = MagicMock(spec=GeminiClient)
    client.generate_content = AsyncMock()
    return client

@pytest.fixture
def mock_db_client():
    client = MagicMock(spec=SurrealDBClient)
    client.query = AsyncMock()
    return client

@pytest.fixture
def dr_mamr_service(mock_gemini_client, mock_db_client):
    return DrMAMRService(mock_gemini_client, mock_db_client)

@pytest.mark.asyncio
async def test_alternating_reasoning_flow(dr_mamr_service, mock_gemini_client, mock_db_client):
    # Setup mocks
    mock_gemini_client.generate_content.side_effect = [
        "Meta Decision 1: Decompose problem", # Meta turn 1
        "Reasoning Step 1: Solving part 1",   # Reasoner turn 1
        "Meta Decision 2: Finalize",          # Meta turn 2
        "Reasoning Step 2: FINAL ANSWER: 42"  # Reasoner turn 2
    ]

    # Run service
    result = await dr_mamr_service.alternating_reasoning("What is the answer?", max_turns=3)

    # Verify calls
    assert mock_gemini_client.generate_content.call_count == 4

    # Verify DB persistence
    assert mock_db_client.query.call_count == 2 # 2 traces saved

    # Verify Result
    assert "42" in result["solution"]
    assert len(result["traces"]) == 2
    assert result["traces"][0]["meta_decision"] == "Meta Decision 1: Decompose problem"
    assert result["traces"][0]["reasoning_step"] == "Reasoning Step 1: Solving part 1"

@pytest.mark.asyncio
async def test_compute_group_advantage(dr_mamr_service):
    # Test high score
    meta = "Plan"
    reasoning = "This is a detailed step-by-step reasoning therefore it is good."
    score = dr_mamr_service._compute_group_advantage(meta, reasoning)
    assert score >= 0.7 # Base 0.5 + 0.1 (step) + 0.2 (therefore) ??

    # Test basic score
    score_basic = dr_mamr_service._compute_group_advantage("Plan", "Short result.")
    assert score_basic == 0.5
