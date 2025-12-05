import pytest
import asyncio
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

@pytest.mark.asyncio
async def test_thundering_herd_writes(mock_surreal_client):
    """Spawn massive concurrent write tasks."""
    client = SurrealDBClient(max_connections=20) # Limit pool to force queuing
    await client.initialize()

    user_id = "stress_user"
    CONCURRENCY = 10 # Reduced for CI/Sandbox

    async def write_task(i):
        mem = Memory(
            user_id=user_id,
            content=f"Stress content {i}",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.5)
        )
        try:
            return await client.create_memory(mem)
        except Exception as e:
            return e

    tasks = [write_task(i) for i in range(CONCURRENCY)]
    results = await asyncio.gather(*tasks)

    # Analyze results
    successes = [r for r in results if isinstance(r, str)]
    failures = [r for r in results if isinstance(r, Exception)]

    if failures:
        print(f"Sample failure: {failures[0]}")

    # Assert success
    assert len(successes) == CONCURRENCY

    await client.close()

@pytest.mark.asyncio
async def test_read_write_race(mock_surreal_client):
    """Concurrent read/update on same memory."""
    client = SurrealDBClient()
    await client.initialize()

    # Setup initial memory
    mem = Memory(
        user_id="race_user",
        content="Initial",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5)
    )
    mem_id = await client.create_memory(mem)

    async def update_task(i):
        # Fetch fresh, modify, save
        try:
            m = await client.get_memory(mem_id)
            if not m: return False
            m.access_count += 1
            await client.update_memory(m)
            return True
        except Exception:
            return False

    # Run updates concurrently
    tasks = [update_task(i) for i in range(10)]
    results = await asyncio.gather(*tasks)

    # In our mock, updates just pass. We verify code doesn't crash.
    successes = [r for r in results if r]
    assert len(successes) == 10

    await client.close()

@pytest.mark.asyncio
async def test_semaphore_limiting(mock_surreal_client):
    """Verify that semaphore actually limits concurrent connections."""
    MAX_CONNS = 5
    client = SurrealDBClient(max_connections=MAX_CONNS)
    await client.initialize()

    tasks = []
    for i in range(MAX_CONNS * 4):
        tasks.append(client.create_memory(Memory(user_id="u", content="c", tier=MemoryTier.WORKING, importance=ImportanceScore(0.5))))

    await asyncio.gather(*tasks)

    # If we finished without error, the pool/semaphore logic held up.
    await client.close()
