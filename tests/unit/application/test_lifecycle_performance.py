
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from khala.application.services.memory_lifecycle import MemoryLifecycleService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

@pytest.mark.asyncio
async def test_lifecycle_consolidation_parallelism():
    """
    Verify that consolidation requests are handled concurrently.
    We'll mock the Gemini client to take some time, and check if total time < sum of times.
    """
    mock_repo = AsyncMock()
    mock_gemini = AsyncMock()

    # Simulate slow LLM response
    async def slow_response(*args, **kwargs):
        await asyncio.sleep(0.1)
        return {"content": "Consolidated content"}

    mock_gemini.generate_text.side_effect = slow_response

    # Create service
    service = MemoryLifecycleService(
        repository=mock_repo,
        gemini_client=mock_gemini
    )

    # Mock finding 5 groups of memories to consolidate
    # We need to mock memory_service.should_consolidate -> True
    # and consolidation_service.group_memories_for_consolidation -> List[List[Memory]]

    service.memory_service.should_consolidate = MagicMock(return_value=True)

    # Create 5 groups of 2 memories each
    groups = []
    for i in range(5):
        m1 = Memory(id=f"m{i}_a", user_id="u1", content=f"Content {i}a", tier=MemoryTier.SHORT_TERM, importance=ImportanceScore(0.5))
        m2 = Memory(id=f"m{i}_b", user_id="u1", content=f"Content {i}b", tier=MemoryTier.SHORT_TERM, importance=ImportanceScore(0.5))
        groups.append([m1, m2])

    service.consolidation_service.group_memories_for_consolidation = MagicMock(return_value=groups)

    # Mock getting memories from repo (doesn't matter much as we mocked grouping)
    mock_repo.get_by_tier.return_value = [m for g in groups for m in g]

    # Measure time
    start_time = asyncio.get_running_loop().time()
    await service.consolidate_memories("u1")
    end_time = asyncio.get_running_loop().time()

    duration = end_time - start_time

    # If sequential: 5 groups * 0.1s = 0.5s
    # If parallel: should be slightly over 0.1s

    print(f"Consolidation duration: {duration:.4f}s")
    assert duration < 0.3, f"Consolidation took too long ({duration:.4f}s), likely sequential."
