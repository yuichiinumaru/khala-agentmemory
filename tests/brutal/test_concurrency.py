import pytest
import asyncio
import random
import string
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@pytest.mark.asyncio
async def test_thundering_herd_writes():
    """Spawn massive concurrent write tasks."""
    client = SurrealDBClient(max_connections=20) # Limit pool to force queuing
    await client.initialize()

    user_id = "stress_user"
    CONCURRENCY = 100 # Adjust based on environment limits

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

    print(f"\nWrite Stress: {len(successes)} successes, {len(failures)} failures")

    if failures:
        print(f"Sample failure: {failures[0]}")

    # In a perfect world, 0 failures. But if pool exhausted, maybe some errors.
    # We assert mostly success.
    assert len(successes) > CONCURRENCY * 0.9

    await client.close()

@pytest.mark.asyncio
async def test_read_write_race():
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

    # Run 50 updates concurrently
    # Note: Without transactions/locking, this implies Last Write Wins.
    # The counter will NOT be +50 accurately, but database shouldn't crash.
    tasks = [update_task(i) for i in range(50)]
    await asyncio.gather(*tasks)

    final_mem = await client.get_memory(mem_id)
    # Counter will likely be < 50 due to race condition overwrite
    print(f"\nFinal Race Counter: {final_mem.access_count}")
    assert final_mem.access_count > 0

    await client.close()
