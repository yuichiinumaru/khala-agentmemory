import pytest
import uuid
import random
import string
from datetime import datetime, timezone
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector
from khala.infrastructure.surrealdb.client import SurrealDBClient

# Helper to generate random string
def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

@pytest.mark.asyncio
async def test_crud_integrity():
    """Test Create, Read, Update, Delete with complex data."""
    client = SurrealDBClient()
    await client.initialize()

    # Create with complex metadata
    user_id = f"user_{random_string()}"
    complex_metadata = {
        "nested": {"a": 1, "b": [1, 2, 3]},
        "unicode": "🚀🔥",
        "large_text": "x" * 1000
    }

    mem = Memory(
        user_id=user_id,
        content="Test Content 🚀",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.8),
        metadata=complex_metadata,
        tags=["test", "brutal"]
    )

    # CREATE
    mem_id = await client.create_memory(mem)
    assert mem_id is not None

    # READ
    fetched = await client.get_memory(mem_id)
    assert fetched is not None
    assert fetched.content == "Test Content 🚀"
    assert fetched.metadata["nested"]["b"] == [1, 2, 3]
    assert fetched.metadata["unicode"] == "🚀🔥"

    # UPDATE
    fetched.content = "Updated Content"
    fetched.metadata["new_field"] = "new_value"
    await client.update_memory(fetched)

    updated = await client.get_memory(mem_id)
    assert updated.content == "Updated Content"
    assert updated.metadata["new_field"] == "new_value"

    # DELETE
    await client.delete_memory(mem_id)
    deleted = await client.get_memory(mem_id)
    assert deleted is None

    await client.close()

@pytest.mark.asyncio
async def test_vector_fidelity():
    """Test that vectors are stored and retrieved with precision."""
    client = SurrealDBClient()
    await client.initialize()

    user_id = f"user_{random_string()}"
    # Generate random vector
    original_vector = [random.random() for _ in range(768)]

    mem = Memory(
        user_id=user_id,
        content="Vector Test",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        embedding=EmbeddingVector(original_vector)
    )

    mem_id = await client.create_memory(mem)
    fetched = await client.get_memory(mem_id)

    assert fetched.embedding is not None
    # Check precision (approximate due to float storage, but should be very close)
    retrieved_vector = fetched.embedding.values

    assert len(retrieved_vector) == len(original_vector)
    for v1, v2 in zip(original_vector, retrieved_vector):
        assert abs(v1 - v2) < 1e-6

    await client.close()

@pytest.mark.asyncio
async def test_filter_logic():
    """Test comprehensive filter operators."""
    client = SurrealDBClient()
    await client.initialize()

    user_id = f"user_{random_string()}"
    base_vec = [0.1] * 768

    # Setup test data
    memories = [
        Memory(user_id=user_id, content="A", tier=MemoryTier.WORKING, importance=ImportanceScore(0.1), metadata={"val": 10, "type": "A"}, embedding=EmbeddingVector(base_vec)),
        Memory(user_id=user_id, content="B", tier=MemoryTier.WORKING, importance=ImportanceScore(0.1), metadata={"val": 20, "type": "B"}, embedding=EmbeddingVector(base_vec)),
        Memory(user_id=user_id, content="C", tier=MemoryTier.WORKING, importance=ImportanceScore(0.1), metadata={"val": 30, "type": "A"}, embedding=EmbeddingVector(base_vec)),
    ]

    for m in memories:
        await client.create_memory(m)

    # Test EQ
    res_eq = await client.search_memories_by_vector(EmbeddingVector(base_vec), user_id, filters={"metadata.val": 20})
    assert len(res_eq) == 1
    assert res_eq[0]['content'] == "B"

    # Test GT
    res_gt = await client.search_memories_by_vector(EmbeddingVector(base_vec), user_id, filters={"metadata.val": {"op": "gt", "value": 15}})
    assert len(res_gt) == 2  # B(20) and C(30)

    # Test IN
    res_in = await client.search_memories_by_vector(EmbeddingVector(base_vec), user_id, filters={"metadata.type": ["A"]})
    assert len(res_in) == 2 # A and C

    await client.close()

@pytest.mark.asyncio
async def test_edge_cases():
    """Test SQL injection resilience and other edges."""
    client = SurrealDBClient()
    await client.initialize()

    user_id = f"user_{random_string()}"

    # Attempt SQL Injection
    nasty_string = "'; DROP TABLE memory; SELECT * FROM memory WHERE content = '"

    mem = Memory(
        user_id=user_id,
        content=nasty_string,
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5)
    )

    # Should not fail and definitely should not drop table
    mem_id = await client.create_memory(mem)
    fetched = await client.get_memory(mem_id)
    assert fetched.content == nasty_string

    # Verify table still exists
    assert await client.get_memory(mem_id) is not None

    await client.close()
