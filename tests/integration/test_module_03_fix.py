"""Integration test for Module 03 fixes."""

import os
os.environ["GOOGLE_API_KEY"] = "dummy"
import pytest
import asyncio
import uuid
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector
from khala.infrastructure.background.jobs.deduplication_job import DeduplicationJob
from khala.infrastructure.background.scheduler import create_scheduler
from khala.infrastructure.background.jobs.job_processor import create_job_processor

@pytest.mark.asyncio
async def test_strict_deduplication_on_create():
    """Verify that creating a duplicate memory returns the existing ID."""
    client = SurrealDBClient(url="ws://localhost:8001/rpc", username="root", password="surrealdb_secret_password")
    await client.initialize()
    async with client.get_connection() as conn:
        await conn.query("REMOVE TABLE memory;")
    
    # Create a unique user_id for this test
    user_id = f"test_user_{uuid.uuid4()}"
    content = f"Unique content for deduplication test {uuid.uuid4()}"
    
    # 1. Create first memory
    m1 = Memory(
        user_id=user_id,
        content=content,
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        embedding=EmbeddingVector(values=[0.1] * 768)
    )
    id1 = await client.create_memory(m1)
    assert id1 is not None
    
    # 2. Try to create duplicate memory
    m2 = Memory(
        user_id=user_id,
        content=content, # Same content
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        embedding=EmbeddingVector(values=[0.1] * 768)
    )
    id2 = await client.create_memory(m2)
    
    # 3. Verify IDs match (strict deduplication)
    assert id1 == id2
    
    # Clean up
    await client.delete_memory(id1)
    await client.close()

@pytest.mark.asyncio
async def test_deduplication_job():
    """Verify DeduplicationJob execution."""
    client = SurrealDBClient(url="ws://localhost:8001/rpc", username="root", password="surrealdb_secret_password")
    await client.initialize()
    
    user_id = f"test_user_job_{uuid.uuid4()}"
    
    # Create two memories with DIFFERENT content but we will manually force one to be a duplicate 
    # logic-wise if we could, but DeduplicationJob uses exact/semantic match.
    # Since we have strict deduplication on create, we can't easily create exact duplicates via client.create_memory.
    # However, we can test that the job runs without error and reports 0 duplicates if none exist.
    
    m1 = Memory(
        user_id=user_id, 
        content=f"Content A {uuid.uuid4()}", 
        tier=MemoryTier.WORKING, 
        importance=ImportanceScore(0.5), 
        embedding=EmbeddingVector(values=[0.1]*768)
    )
    await client.create_memory(m1)
    
    job = DeduplicationJob(client)
    result = await job.execute({"user_id": user_id})
    
    assert result["status"] == "completed"
    assert result["users_processed"] == 1
    assert result["duplicates_removed"] == 0 # Should be 0 as we can't create duplicates easily now!
    
    await client.close()

@pytest.mark.asyncio
async def test_scheduler_registration():
    """Verify scheduler registers deduplication task."""
    # We don't need real redis for this check
    processor = create_job_processor(redis_url="redis://localhost:6379/1") 
    scheduler = create_scheduler(processor)
    
    assert "weekly_deduplication" in scheduler.tasks
    task = scheduler.tasks["weekly_deduplication"]
    assert task.job_type == "deduplication"
    assert task.payload == {"scan_all": True}
