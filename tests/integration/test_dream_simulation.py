
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from khala.application.services.dream_service import DreamService
from khala.domain.memory.entities import Memory, MemorySource
from khala.domain.memory.value_objects import MemoryTier, ImportanceScore
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient

@pytest.mark.asyncio
async def test_consolidate_dreams():
    # Mock Dependencies
    mock_db = MagicMock(spec=SurrealDBClient)
    mock_llm = MagicMock(spec=GeminiClient)

    service = DreamService(db_client=mock_db, llm_client=mock_llm)

    # 1. Setup Mock Memories
    mock_memories = [
        Memory(
            id=f"mem_{i}",
            user_id="test_agent",
            content=f"Memory content {i}",
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.medium(),
            source=MemorySource(source_type="user"),
            created_at=datetime.now(timezone.utc)
        )
        for i in range(10)
    ]

    mock_db.search_memories = AsyncMock(return_value=mock_memories)

    # Mock LLM Response
    mock_response = MagicMock()
    mock_response.text = "This is a dream narrative. Analysis: Meaningful."
    mock_llm.generate_content = AsyncMock(return_value=mock_response)

    # Mock DB Create
    async def mock_create_memory(memory):
        memory.id = "dream_123"
        return memory
    mock_db.create_memory = AsyncMock(side_effect=mock_create_memory)

    # 2. Execute
    dream = await service.consolidate_dreams(agent_id="test_agent", memory_count=3)

    # 3. Verify
    assert dream is not None
    assert dream.id == "dream_123"
    assert dream.tier == MemoryTier.SHORT_TERM
    assert dream.metadata["type"] == "dream_consolidation"
    assert "dream" in dream.tags
    assert len(dream.metadata["source_memories"]) == 3

    mock_db.search_memories.assert_called_once()
    mock_llm.generate_content.assert_called_once()
    mock_db.create_memory.assert_called_once()


@pytest.mark.asyncio
async def test_simulate_counterfactual():
    # Mock Dependencies
    mock_db = MagicMock(spec=SurrealDBClient)
    mock_llm = MagicMock(spec=GeminiClient)

    service = DreamService(db_client=mock_db, llm_client=mock_llm)

    # 1. Setup Mock Episode Memories
    mock_memories = [
        Memory(
            id=f"ep_mem_{i}",
            user_id="test_agent",
            content=f"Episode step {i}",
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.medium(),
            source=MemorySource(source_type="system"),
            created_at=datetime.now(timezone.utc)
        )
        for i in range(3)
    ]

    mock_db.search_memories = AsyncMock(return_value=mock_memories)

    # Mock LLM Response
    mock_response = MagicMock()
    mock_response.text = "Counterfactual: What if step 1 failed? Lesson: Prepare better."
    mock_llm.generate_content = AsyncMock(return_value=mock_response)

    # Mock DB Create
    async def mock_create_memory(memory):
        memory.id = "sim_456"
        return memory
    mock_db.create_memory = AsyncMock(side_effect=mock_create_memory)

    # 2. Execute
    simulation = await service.simulate_counterfactual(episode_id="ep_123", agent_id="test_agent")

    # 3. Verify
    assert simulation is not None
    assert simulation.id == "sim_456"
    assert simulation.metadata["type"] == "counterfactual_simulation"
    assert simulation.metadata["episode_id"] == "ep_123"
    assert simulation.metadata["is_hypothetical"] is True

    mock_db.search_memories.assert_called_once()
    # Check if filter was passed correctly
    call_kwargs = mock_db.search_memories.call_args[1]
    assert call_kwargs["filters"] == {"episode_id": "ep_123"}

    mock_llm.generate_content.assert_called_once()
    mock_db.create_memory.assert_called_once()
