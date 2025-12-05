
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from khala.application.services.deduplication_service import DeduplicationService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector
from datetime import datetime

@pytest.mark.asyncio
async def test_deduplication_exact_match():
    # Mock DB Client
    mock_db = AsyncMock()

    # Setup service
    service = DeduplicationService(mock_db)

    # Mock exact match found
    mock_connection = AsyncMock()
    mock_connection.query.return_value = [{'status': 'OK', 'result': [{'id': 'memory:existing_123'}]}]

    # Mock get_connection to return an async context manager properly
    # The client method is defined as @asynccontextmanager, so calling it returns an async context manager.
    # In the mock, we need to make sure `db.get_connection()` returns an object that has __aenter__ and __aexit__.
    # Since `db.get_connection` is an AsyncMock method, calling it returns a coroutine by default unless we set a return value.
    # But wait, we want `async with db.get_connection()`.
    # If `db.get_connection` is an AsyncMock, calling it returns a coroutine (which we see in the error).
    # We should make `db.get_connection` a standard Mock that returns an AsyncMock (which acts as the context manager).

    mock_db.get_connection = MagicMock()
    mock_db.get_connection = MagicMock()
    mock_db.get_connection = MagicMock()
    mock_db.get_connection.return_value = mock_connection
    mock_connection.__aenter__.return_value = mock_connection
    mock_connection.__aexit__.return_value = None

    # Create test memory
    memory = Memory(
        id="new_mem",
        user_id="user1",
        content="Hello World",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.low(),
        embedding=None,
        created_at=datetime.now(),
        updated_at=datetime.now(),
        accessed_at=datetime.now()
    )

    # Run check
    result = await service.check_duplicate(memory)

    assert result.is_duplicate is True
    assert result.duplicate_of_id == "existing_123"
    assert result.duplicate_type == "exact"

@pytest.mark.asyncio
async def test_deduplication_semantic_match():
    # Mock DB Client
    mock_db = AsyncMock()
    service = DeduplicationService(mock_db, semantic_threshold=0.9)

    # Mock exact match NOT found
    mock_connection = AsyncMock()
    mock_connection.query.return_value = []

    # Mock get_connection to be an async context manager
    mock_db.get_connection = MagicMock()
    mock_db.get_connection = MagicMock()
    mock_db.get_connection.return_value = mock_connection
    mock_connection.__aenter__.return_value = mock_connection
    mock_connection.__aexit__.return_value = None

    # Mock semantic match found via client method
    mock_db.search_memories_by_vector.return_value = [
        {'id': 'memory:semantic_123', 'similarity': 0.95}
    ]

    # Create test memory
    memory = Memory(
        id="new_mem",
        user_id="user1",
        content="Hi World",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.low(),
        embedding=EmbeddingVector([0.1, 0.2, 0.3]),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        accessed_at=datetime.now()
    )

    # Run check
    result = await service.check_duplicate(memory)

    assert result.is_duplicate is True
    assert result.duplicate_of_id == "semantic_123"
    assert result.duplicate_type == "semantic"
    assert result.similarity_score == 0.95

@pytest.mark.asyncio
async def test_no_duplicate():
    # Mock DB Client
    mock_db = AsyncMock()
    service = DeduplicationService(mock_db)

    mock_connection = AsyncMock()
    mock_connection.query.return_value = []

    # Mock get_connection to be an async context manager
    mock_db.get_connection = MagicMock()
    mock_db.get_connection.return_value = mock_connection
    mock_connection.__aenter__.return_value = mock_connection
    mock_connection.__aexit__.return_value = None

    mock_db.search_memories_by_vector.return_value = []

    memory = Memory(
        id="new_mem",
        user_id="user1",
        content="Unique Content",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.low(),
        embedding=EmbeddingVector([0.1, 0.2, 0.3]),
        created_at=datetime.now(),
        updated_at=datetime.now(),
        accessed_at=datetime.now()
    )

    result = await service.check_duplicate(memory)

    assert result.is_duplicate is False
