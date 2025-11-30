
import pytest
import asyncio
from unittest.mock import AsyncMock, Mock, patch, MagicMock
from khala.infrastructure.background.jobs.job_processor import JobProcessor, JobDefinition, JobPriority, JobResult, JobStatus
from khala.infrastructure.background.scheduler import BackgroundScheduler

@pytest.fixture
def mock_db_client():
    client = AsyncMock()
    # Mock connection context manager
    connection_mock = AsyncMock()
    connection_mock.query = AsyncMock()

    # client.get_connection() is called in "async with"
    # It should return an async context manager.
    # When mocking an async function that returns a context manager:

    # Define a helper class for AsyncContextManager
    class AsyncContextManager:
        async def __aenter__(self):
            return connection_mock
        async def __aexit__(self, exc_type, exc, tb):
            pass

    # Make get_connection return this context manager when CALLED
    # Since get_connection is defined as async def in the real class but used as @asynccontextmanager
    # In the code: async with self.db_client.get_connection() as conn:
    # This implies get_connection() returns an object with __aenter__

    # However, if client.get_connection is an AsyncMock, calling it returns a Coroutine/AsyncMock.
    # We need to make the return value of the CALL be the context manager.

    client.get_connection.return_value = AsyncContextManager()

    # BUT, wait. If get_connection is NOT an async function but decorated with @asynccontextmanager,
    # calling it returns an async generator/context manager immediately.
    # The code `async with self.db_client.get_connection()` expects the result of the call to be the CM.

    return client

@pytest.fixture
def job_processor(mock_db_client):
    processor = JobProcessor(redis_url="redis://localhost:6379", max_workers=1)
    processor.db_client = mock_db_client
    # Mock redis client to avoid real connection
    processor.redis_client = AsyncMock()
    return processor

@pytest.mark.asyncio
async def test_job_execution_consolidation(job_processor):
    # Mock MemoryLifecycleService
    with patch('khala.application.services.memory_lifecycle.MemoryLifecycleService') as MockLifecycle:
        mock_lifecycle_instance = MockLifecycle.return_value
        mock_lifecycle_instance.consolidate_memories = AsyncMock(return_value=5)

        job = JobDefinition(
            job_id="test_consolidation",
            job_type="consolidation",
            job_class="ConsolidationJob",
            priority=JobPriority.LOW,
            payload={"user_id": "user123"},
            created_at=None
        )

        result = await job_processor._execute_consolidation(job)

        assert result.success is True
        assert result.result["memories_consolidated"] == 5
        mock_lifecycle_instance.consolidate_memories.assert_awaited_once_with("user123")

@pytest.mark.asyncio
async def test_job_execution_deduplication(job_processor):
    # Mock MemoryLifecycleService
    with patch('khala.application.services.memory_lifecycle.MemoryLifecycleService') as MockLifecycle:
        mock_lifecycle_instance = MockLifecycle.return_value
        mock_lifecycle_instance.deduplicate_memories = AsyncMock(return_value=3)

        job = JobDefinition(
            job_id="test_dedup",
            job_type="deduplication",
            job_class="DeduplicationJob",
            priority=JobPriority.LOW,
            payload={"user_id": "user123"},
            created_at=None
        )

        result = await job_processor._execute_deduplication(job)

        assert result.success is True
        assert result.result["duplicates_removed"] == 3
        mock_lifecycle_instance.deduplicate_memories.assert_awaited_once_with("user123")

@pytest.mark.asyncio
async def test_job_execution_decay_scan_all(job_processor):
    # Prepare the mock connection and context manager for THIS specific test
    mock_conn = AsyncMock()
    mock_conn.query.return_value = [{"result": [{"id": "memory:1"}, {"id": "memory:2"}]}]

    class AsyncContextManager:
        async def __aenter__(self):
            return mock_conn
        async def __aexit__(self, *args):
            pass

    # Override the fixture's setup
    job_processor.db_client.get_connection = Mock(return_value=AsyncContextManager())

    # Mock TemporalAnalysisService
    with patch('khala.infrastructure.background.jobs.job_processor.TemporalAnalysisService') as MockTemporal:
        mock_temporal_instance = MockTemporal.return_value
        mock_temporal_instance.batch_process_decay = AsyncMock(return_value={"processed": 2})

        job = JobDefinition(
            job_id="test_decay",
            job_type="decay_scoring",
            job_class="DecayScoringJob",
            priority=JobPriority.LOW,
            payload={"scan_all": True},
            created_at=None
        )

        result = await job_processor._execute_decay_scoring(job)

        assert result.success is True
        assert result.result["processed"] == 2
        mock_temporal_instance.batch_process_decay.assert_awaited_once()
        # Check that DB was queried for IDs
        mock_conn.query.assert_awaited()
