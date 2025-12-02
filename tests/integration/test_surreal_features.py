import pytest
import asyncio
from datetime import datetime, timezone
import uuid

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import MemorySource, Sentiment, EmbeddingVector

@pytest.mark.asyncio
async def test_memory_versioning():
    client = SurrealDBClient()
    await client.initialize()

    # Create memory with dummy embedding to satisfy schema
    embedding = EmbeddingVector(values=[0.1] * 768)

    memory = Memory(
        user_id="user_test_ver",
        content="Original content",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        embedding=embedding
    )
    memory_id = await client.create_memory(memory)

    # Update memory
    memory.content = "Updated content"
    memory.importance = ImportanceScore(0.8)
    await client.update_memory(memory)

    # Verify versioning
    # Verify DB state
    query = "SELECT * FROM type::thing('memory', $id)"
    async with client.get_connection() as conn:
        result = await conn.query(query, {"id": memory_id})
        record = result[0] if isinstance(result, list) and result else None

        assert record is not None
        assert "versions" in record
        assert len(record["versions"]) == 1
        assert record["versions"][0]["content"] == "Original content"
        assert record["versions"][0]["reason"] == "update"

    await client.close()

@pytest.mark.asyncio
async def test_memory_events():
    client = SurrealDBClient()
    await client.initialize()

    embedding = EmbeddingVector(values=[0.1] * 768)

    memory = Memory(
        user_id="user_test_evt",
        content="Event test content",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        embedding=embedding
    )
    memory_id = await client.create_memory(memory)

    # Add event
    await client.add_memory_event(memory_id, "accessed", {"by": "agent_1"})

    # Verify event
    query = "SELECT * FROM type::thing('memory', $id)"
    async with client.get_connection() as conn:
        result = await conn.query(query, {"id": memory_id})
        record = result[0]

        assert "events" in record
        assert len(record["events"]) == 1
        assert record["events"][0]["event_type"] == "accessed"
        assert record["events"][0]["payload"]["by"] == "agent_1"

    await client.close()

@pytest.mark.asyncio
async def test_computed_fields():
    client = SurrealDBClient()
    await client.initialize()

    embedding = EmbeddingVector(values=[0.1] * 768)

    memory = Memory(
        user_id="user_test_comp",
        content="Computed field test",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(1.0), # High importance
        embedding=embedding
    )
    memory_id = await client.create_memory(memory)

    # Query to check decay_score (computed on read/select usually if defined as VALUE)
    # The schema defines: DEFINE FIELD decay_score ON memory VALUE fn::decay_score(...)
    # So it should be present in the SELECT * result.

    query = "SELECT *, decay_score FROM type::thing('memory', $id)"
    async with client.get_connection() as conn:
        result = await conn.query(query, {"id": memory_id})
        record = result[0]

        # Verify decay_score exists
        assert "decay_score" in record
        # Initially it should be close to importance (1.0) as age is 0
        assert record["decay_score"] > 0.9

    await client.close()

@pytest.mark.asyncio
async def test_nested_documents():
    client = SurrealDBClient()
    await client.initialize()

    embedding = EmbeddingVector(values=[0.1] * 768)

    source = MemorySource(
        source_type="user_input",
        source_id="msg_123",
        timestamp=datetime.now(timezone.utc)
    )
    sentiment = Sentiment(
        score=0.8,
        label="joy",
        emotions={"joy": 0.8, "excitement": 0.5}
    )

    memory = Memory(
        user_id="user_test_nest",
        content="Nested test",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        source=source,
        sentiment=sentiment,
        embedding=embedding
    )
    memory_id = await client.create_memory(memory)

    # Fetch and verify
    fetched_memory = await client.get_memory(memory_id)

    assert fetched_memory is not None
    assert fetched_memory.source is not None
    assert fetched_memory.source.source_type == "user_input"
    assert fetched_memory.sentiment is not None
    assert fetched_memory.sentiment.label == "joy"

    await client.close()
