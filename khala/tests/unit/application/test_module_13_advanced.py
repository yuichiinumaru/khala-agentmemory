"""Integration tests for Module 13.2 & 13.3 (Graph & Collaboration)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.application.services.graph_reasoning import KnowledgeGraphReasoningService
from khala.application.services.graph_token_service import GraphTokenService
from khala.infrastructure.persistence.latent_repository import LatentRepository, LatentState
from khala.application.coordination.hierarchical_team import HierarchicalTeamService

@pytest.mark.asyncio
async def test_graph_reasoning_flow():
    # Mock
    mock_db = MagicMock(spec=SurrealDBClient)
    mock_conn = AsyncMock()
    mock_db.get_connection.return_value.__aenter__.return_value = mock_conn

    # Mock DB response for path finding
    mock_conn.query.return_value = [{"result": [{"path": [{"id": "e2"}]}]}]

    mock_gemini = MagicMock(spec=GeminiClient)
    mock_response = MagicMock()
    mock_response.text = "The best path is Path 0 because..."
    mock_gemini.generate_content = AsyncMock(return_value=mock_response)

    service = KnowledgeGraphReasoningService(mock_db, mock_gemini)

    # We rely on the internal simulated path finding for this test since we mocked DB
    result = await service.reason_over_graph("entity:123", "Why X?", max_hops=2)

    assert "best_path" in result
    assert "explanation" in result
    assert mock_gemini.generate_content.called
    assert mock_conn.query.called # Trace saving

@pytest.mark.asyncio
async def test_graph_token_service():
    mock_db = MagicMock(spec=SurrealDBClient)
    mock_conn = AsyncMock()
    mock_db.get_connection.return_value.__aenter__.return_value = mock_conn

    # Mock DB response for _fetch_embedding (kg_embeddings query)
    mock_conn.query.return_value = [{"result": [{"entity_text": ["Entity 1"], "embedding": [0.1, 0.2]}]}]

    service = GraphTokenService(mock_db)

    tokens = await service.get_kg_tokens(["e1"])

    assert "<kg_context>" in tokens
    assert "Entity 1" in tokens
    assert "</kg_context>" in tokens

@pytest.mark.asyncio
async def test_latent_repository():
    mock_db = MagicMock(spec=SurrealDBClient)
    mock_conn = AsyncMock()
    mock_db.get_connection.return_value.__aenter__.return_value = mock_conn

    repo = LatentRepository(mock_db)

    state = LatentState(
        agent_id="agent-1",
        iteration=1,
        state_embedding=[0.1, 0.2],
        decision_made="move_left",
        created_at=datetime.now(timezone.utc)
    )

    await repo.store_state(state)
    assert mock_conn.query.called

@pytest.mark.asyncio
async def test_hierarchical_team():
    mock_db = MagicMock(spec=SurrealDBClient)
    mock_conn = AsyncMock()
    mock_db.get_connection.return_value.__aenter__.return_value = mock_conn

    service = HierarchicalTeamService(mock_db)

    await service.register_guidance("dec-1", "act-1", "constraint")
    assert mock_conn.query.called
