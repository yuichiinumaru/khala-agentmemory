import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.recursive_summary_service import RecursiveSummaryService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

@pytest.fixture
def mock_repo():
    repo = MagicMock()
    repo.get_by_id = AsyncMock()
    repo.create = AsyncMock()
    return repo

@pytest.fixture
def mock_gemini():
    client = MagicMock()
    client.generate_text = AsyncMock(return_value={"content": "Summary"})
    return client

def test_summarize_simple(mock_repo, mock_gemini):
    asyncio.run(_test_summarize_simple(mock_repo, mock_gemini))

async def _test_summarize_simple(mock_repo, mock_gemini):
    service = RecursiveSummaryService(mock_repo, mock_gemini)

    # Setup mock memories
    mem1 = Memory(user_id="u1", content="A", tier=MemoryTier.WORKING, importance=ImportanceScore.medium())
    mem2 = Memory(user_id="u1", content="B", tier=MemoryTier.WORKING, importance=ImportanceScore.medium())

    async def get_mem(id):
        return mem1 if id == "1" else mem2
    mock_repo.get_by_id.side_effect = get_mem

    result = await service.summarize_memories(["1", "2"], "u1", chunk_size=5)

    assert result.content == "Summary"
    assert result.metadata["is_summary"] is True
    assert result.metadata["recursion_depth"] == 0

def test_summarize_recursive(mock_repo, mock_gemini):
    asyncio.run(_test_summarize_recursive(mock_repo, mock_gemini))

async def _test_summarize_recursive(mock_repo, mock_gemini):
    service = RecursiveSummaryService(mock_repo, mock_gemini)

    # 6 items, chunk size 5 -> 2 chunks -> 2 intermediate summaries -> 1 final summary
    mem = Memory(user_id="u1", content="X", tier=MemoryTier.WORKING, importance=ImportanceScore.medium())
    mock_repo.get_by_id.return_value = mem

    ids = [str(i) for i in range(6)]

    result = await service.summarize_memories(ids, "u1", chunk_size=5)

    assert result.content == "Summary"
    assert result.metadata["recursion_depth"] == 1 # Depth 1 means summaries of summaries
