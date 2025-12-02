
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, Mock, patch
from khala.application.services.memory_lifecycle import MemoryLifecycleService
from khala.domain.memory.entities import Memory, MemoryTier
from khala.domain.memory.services import MemoryService, ConsolidationService

@pytest.fixture
def mock_repository():
    return AsyncMock()

@pytest.fixture
def mock_gemini_client():
    return AsyncMock()

@pytest.fixture
def mock_memory_service():
    service = Mock(spec=MemoryService)
    service.should_consolidate.return_value = True
    return service

@pytest.fixture
def mock_consolidation_service():
    service = Mock(spec=ConsolidationService)
    return service

@pytest.mark.asyncio
async def test_consolidate_memories(mock_repository, mock_gemini_client, mock_memory_service, mock_consolidation_service):
    service = MemoryLifecycleService(
        repository=mock_repository,
        gemini_client=mock_gemini_client,
        memory_service=mock_memory_service,
        consolidation_service=mock_consolidation_service
    )

    # Setup memories
    memories = [
        Memory(user_id="user1", content="Memory 1", tier=MemoryTier.SHORT_TERM, importance=0.5),
        Memory(user_id="user1", content="Memory 2", tier=MemoryTier.SHORT_TERM, importance=0.6)
    ]

    mock_repository.get_by_tier.return_value = memories
    mock_consolidation_service.group_memories_for_consolidation.return_value = [memories]

    # Mock LLM response
    mock_gemini_client.generate_text.return_value = {"content": "Consolidated memory content"}

    count = await service.consolidate_memories("user1")

    assert count == 2
    mock_gemini_client.generate_text.assert_called_once()
    mock_repository.create.assert_called_once()
    assert mock_repository.update.call_count == 2 # Archives original memories

@pytest.mark.asyncio
async def test_consolidate_memories_with_approval(mock_repository, mock_gemini_client, mock_memory_service, mock_consolidation_service):
    mock_approval_service = AsyncMock()

    service = MemoryLifecycleService(
        repository=mock_repository,
        gemini_client=mock_gemini_client,
        memory_service=mock_memory_service,
        consolidation_service=mock_consolidation_service,
        approval_service=mock_approval_service
    )

    # Setup memories
    memories = [
        Memory(user_id="user1", content="Memory 1", tier=MemoryTier.SHORT_TERM, importance=0.5),
        Memory(user_id="user1", content="Memory 2", tier=MemoryTier.SHORT_TERM, importance=0.6)
    ]

    mock_repository.get_by_tier.return_value = memories
    mock_consolidation_service.group_memories_for_consolidation.return_value = [memories]

    # Mock LLM response
    mock_gemini_client.generate_text.return_value = {"content": "Consolidated memory content"}

    count = await service.consolidate_memories("user1")

    # Should request approval and NOT create/update memories
    assert count == 0
    mock_gemini_client.generate_text.assert_called_once()
    mock_approval_service.request_approval.assert_called_once()
    mock_repository.create.assert_not_called()
    mock_repository.update.assert_not_called()
