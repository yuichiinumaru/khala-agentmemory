import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
import json

from khala.application.services.intent_classifier import IntentClassifier, QueryIntent
from khala.application.services.sop_service import SOPService
from khala.application.services.hypothesis_service import HypothesisService
from khala.application.services.user_profile_service import UserProfileService
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.domain.instruction.repository import InstructionRepository
from khala.domain.instruction.entities import Instruction

# --- Mocks ---

@pytest.fixture
def mock_db_client():
    client = MagicMock(spec=SurrealDBClient)
    client.create = AsyncMock(return_value={"id": "mock_id"})
    client.select = AsyncMock(return_value=None)
    client.update = AsyncMock(return_value={"id": "mock_id"})
    client.delete = AsyncMock(return_value=True)

    mock_conn = AsyncMock()
    client.get_connection = MagicMock()
    client.get_connection.return_value.__aenter__.return_value = mock_conn
    client.get_connection.return_value.__aexit__.return_value = None

    return client

@pytest.fixture
def mock_gemini():
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock(return_value={"content": "{}"})
    return client

@pytest.fixture
def mock_instruction_repo():
    repo = MagicMock(spec=InstructionRepository)
    repo.get_by_id = AsyncMock(return_value=None)
    return repo

# --- IntentClassifier Tests ---

@pytest.mark.asyncio
async def test_intent_classification(mock_gemini):
    service = IntentClassifier(mock_gemini)

    # Mock LLM response
    mock_gemini.generate_text.return_value = {
        "content": '{"intent": "ANALYSIS", "confidence": 0.9, "reasoning": "Deep question"}'
    }

    result = await service.classify_intent("Analyze the impact of X on Y")

    assert result["intent"] == "analysis"
    assert result["confidence"] == 0.9
    assert mock_gemini.generate_text.called

# --- SOPService Tests ---

@pytest.mark.asyncio
async def test_sop_creation(mock_db_client, mock_instruction_repo):
    service = SOPService(mock_db_client, mock_instruction_repo)

    sop = await service.create_sop(
        name="Deploy",
        description="Deployment procedure",
        steps=["Build", "Test", "Push"],
        role="DevOps"
    )

    assert sop.name == "Deploy"
    assert len(sop.steps) == 3
    assert mock_db_client.create.called

@pytest.mark.asyncio
async def test_sop_execution_simulation(mock_db_client, mock_instruction_repo):
    service = SOPService(mock_db_client, mock_instruction_repo)

    # Mock get_sop return
    mock_db_client.select.return_value = {
        "id": "sop:1",
        "name": "Test SOP",
        "description": "Desc",
        "steps": ["Step 1", "Step 2"],
        "required_role": "user",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "metadata": {}
    }

    trace = await service.execute_sop("sop:1", {})

    assert trace["sop_id"] == "sop:1"
    assert len(trace["steps_executed"]) == 2
    assert trace["status"] == "completed"

# --- HypothesisService Tests ---

@pytest.mark.asyncio
async def test_hypothesis_generation(mock_gemini, mock_db_client):
    service = HypothesisService(mock_gemini, mock_db_client)

    mock_gemini.generate_text.return_value = {
        "content": '{"hypothesis": "The sky is blue due to Rayleigh scattering", "confidence": 0.95}'
    }

    result = await service.generate_hypothesis("Why is the sky blue?", [])

    assert "hypothesis" in result
    assert result["confidence"] == 0.95

# --- UserProfileService Tests ---

@pytest.mark.asyncio
async def test_user_profile_management(mock_db_client):
    service = UserProfileService(mock_db_client)

    # Test get/create default
    mock_db_client.select.return_value = None # Not found
    profile = await service.get_profile("user:123")

    assert profile.user_id == "user:123"
    assert profile.knowledge_level == "intermediate"

    # Test update preference
    await service.update_preference("user:123", "theme", "dark")

    # Verify update called
    assert mock_db_client.update.called or mock_db_client.create.called
