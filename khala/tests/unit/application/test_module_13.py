"""Integration tests for Module 13 (PromptWizard & ARM)."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.application.services.prompt_optimization import PromptOptimizationService
from khala.domain.prompt.entities import PromptCandidate
from khala.application.services.reasoning_discovery import ReasoningDiscoveryService

@pytest.mark.asyncio
async def test_prompt_optimization_flow():
    # Mock dependencies
    mock_db = MagicMock(spec=SurrealDBClient)
    mock_conn = AsyncMock()
    mock_db.get_connection.return_value.__aenter__.return_value = mock_conn

    mock_gemini = MagicMock(spec=GeminiClient)
    mock_response = MagicMock()
    mock_response.text = "Optimized Prompt"
    mock_gemini.generate_content = AsyncMock(return_value=mock_response)

    # Initialize Service
    service = PromptOptimizationService(mock_db, mock_gemini)

    # 1. Test Initialization
    candidates = await service.initialize_population(
        task_id="task-123",
        initial_prompts=["Base Prompt"],
        base_instructions="Be helpful."
    )

    assert len(candidates) == 1
    assert candidates[0].prompt_text == "Base Prompt"
    assert candidates[0].generation == 0
    # Verify DB call
    assert mock_conn.query.called

    # 2. Test Evolution Loop (Mocking query return)
    # Mock returning the population we just "saved"
    candidate_data = [
        {
            "id": "cand-1",
            "task_id": "task-123",
            "prompt_text": "Base Prompt",
            "instructions": "Be helpful.",
            "generation": 0,
            "fitness_score": 0.5,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
    ]
    mock_conn.query.return_value = candidate_data

    # Run evolution
    new_population = await service.evolve_prompts(
        task_id="task-123",
        num_generations=1
    )

    # Should have evolved
    assert len(new_population) > 0
    assert mock_gemini.generate_content.called # Mutation happened

@pytest.mark.asyncio
async def test_reasoning_discovery():
    # Mock dependencies
    mock_db = MagicMock(spec=SurrealDBClient)
    mock_conn = AsyncMock()
    mock_db.get_connection.return_value.__aenter__.return_value = mock_conn

    mock_gemini = MagicMock(spec=GeminiClient)
    mock_response = MagicMock()
    mock_response.text = "class Solver:\n    def solve(self, data): return {}"
    mock_gemini.generate_content = AsyncMock(return_value=mock_response)

    service = ReasoningDiscoveryService(mock_db, mock_gemini)

    modules = await service.discover_modules("Solve math problems")

    assert len(modules) == 1
    assert "class Solver" in modules[0].module_code
    assert mock_conn.query.called
