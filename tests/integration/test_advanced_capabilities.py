import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from datetime import datetime, timezone

from khala.application.services.task_decomposition_service import TaskDecompositionService
from khala.application.services.hypothesis_service import HypothesisService
from khala.application.services.tool_selection_service import ToolSelectionService
from khala.domain.memory.entities import Memory, MemoryTier, Relationship
from khala.domain.memory.value_objects import ImportanceScore

@pytest.fixture
def mock_gemini_client():
    client = MagicMock()
    client.generate_text = AsyncMock()
    return client

@pytest.fixture
def mock_db_client():
    client = MagicMock()
    client.create_memory = AsyncMock(side_effect=lambda m: f"memory:{m.id}" if not m.id.startswith("memory:") else m.id)
    client.create_relationship = AsyncMock(return_value="rel:123")
    return client

@pytest.fixture
def mock_search_service():
    service = MagicMock()
    service.search = AsyncMock()
    return service

@pytest.mark.asyncio
async def test_task_decomposition_service(mock_gemini_client, mock_db_client):
    # Setup
    service = TaskDecompositionService(mock_gemini_client, mock_db_client)

    # Mock LLM response
    mock_gemini_client.generate_text.return_value = {
        "content": """
        [
            {"title": "Step 1", "description": "Do first thing", "estimated_complexity": "Low", "priority": "High"},
            {"title": "Step 2", "description": "Do second thing", "estimated_complexity": "Medium", "priority": "Medium"}
        ]
        """
    }

    # Execute
    memories = await service.decompose_goal("Build a rocket", "user1")

    # Verify
    assert len(memories) == 3 # 1 Goal + 2 Subtasks
    assert memories[0].content == "Goal: Build a rocket"
    assert memories[0].metadata["type"] == "goal"

    assert memories[1].content.startswith("Subtask: Step 1")
    assert memories[1].metadata["type"] == "subtask"

    # Verify DB calls
    assert mock_db_client.create_memory.call_count == 3
    assert mock_db_client.create_relationship.call_count == 4 # 2 subtasks * 2 directions

@pytest.mark.asyncio
async def test_hypothesis_service(mock_gemini_client, mock_search_service):
    import json
    # Setup
    service = HypothesisService(mock_gemini_client, mock_search_service)

    # Mock formulate hypothesis
    mock_gemini_client.generate_text.side_effect = [
        {"content": "The sky is blue because of Rayleigh scattering."}, # Formulation
        {"content": json.dumps({ # Evaluation
            "verdict": "Supported",
            "confidence": 0.95,
            "reasoning": "Evidence matches theory.",
            "key_evidence_ids": ["mem1"]
        })}
    ]

    # Mock Search
    mock_search_service.search.return_value = [
        Memory(
            user_id="user1",
            content="Rayleigh scattering causes blue sky.",
            tier=MemoryTier.LONG_TERM,
            importance=ImportanceScore(0.8),
            id="mem1"
        )
    ]

    import json

    # Execute
    result = await service.run_investigation("Why is sky blue?", "user1")

    # Verify
    assert result["hypothesis"] == "The sky is blue because of Rayleigh scattering."
    assert result["verdict"] == "Supported"
    assert result["confidence"] == 0.95

    mock_search_service.search.assert_called_once()
    assert mock_gemini_client.generate_text.call_count == 2

@pytest.mark.asyncio
async def test_tool_selection_service(mock_gemini_client):
    # Setup
    service = ToolSelectionService(mock_gemini_client)

    # Mock LLM response
    mock_gemini_client.generate_text.return_value = {
        "content": """
        [
            {"name": "search_memories", "reason": "Need to find facts."},
            {"name": "test_hypothesis", "reason": "Need to verify theory."}
        ]
        """
    }

    # Execute
    selected = await service.select_tools("Is the earth flat?", [])

    # Verify
    assert len(selected) == 2
    assert selected[0]["name"] == "search_memories"
    assert selected[1]["name"] == "test_hypothesis"
