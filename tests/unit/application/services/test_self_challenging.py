import pytest
from unittest.mock import AsyncMock, MagicMock
from khala.application.services.self_challenging_service import SelfChallengingService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

@pytest.fixture
def service():
    mock_client = AsyncMock()
    return SelfChallengingService(mock_client)

@pytest.mark.asyncio
async def test_challenge_passes(service):
    # Mock LLM saying "VERIFIED"
    service.client.generate_text.return_value = {"content": "VERIFIED: This memory answers the query."}

    memory = Memory(user_id="u1", content="Paris is in France.", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5))
    query = "Where is Paris?"

    result = await service.challenge_memory(query, memory)
    assert result is True

@pytest.mark.asyncio
async def test_challenge_fails(service):
    # Mock LLM saying "REJECTED"
    service.client.generate_text.return_value = {"content": "REJECTED: Context mismatch."}

    memory = Memory(user_id="u1", content="Paris is in Texas.", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5))
    query = "What is the capital of France?"

    result = await service.challenge_memory(query, memory)
    assert result is False
