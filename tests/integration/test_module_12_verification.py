import pytest
import pytest_asyncio
import os
import uuid
from datetime import datetime, timezone
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.surrealdb.schema import DatabaseSchema
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

# Use the same SurrealDB configuration as Module 11
SURREALDB_URL = os.getenv("SURREALDB_URL", "ws://localhost:8001/rpc")
SURREAL_USER = "root"
SURREAL_PASS = "surrealdb_secret_password"
SURREAL_NS = "test_ns_mod12"
SURREAL_DB = "test_db_mod12"

@pytest_asyncio.fixture
async def db_client():
    client = SurrealDBClient(
        url=SURREALDB_URL,
        username=SURREAL_USER,
        password=SURREAL_PASS,
        namespace=SURREAL_NS,
        database=SURREAL_DB
    )
    await client.initialize()
    
    # Initialize schema
    schema = DatabaseSchema(client)
    await schema.create_schema()
    
    yield client
    
    # Cleanup
    async with client.get_connection() as conn:
        await conn.query("REMOVE TABLE memory")
        await conn.query("REMOVE TABLE entity")
        await conn.query("REMOVE TABLE relationship")

@pytest.mark.asyncio
async def test_episodic_memory(db_client):
    """Verify storage and retrieval of episode_id."""
    episode_id = f"ep_{uuid.uuid4()}"
    
    memory1 = Memory(
        user_id="user_123",
        content="First memory of the episode",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.high(),
        episode_id=episode_id
    )
    
    memory2 = Memory(
        user_id="user_123",
        content="Second memory of the episode",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.medium(),
        episode_id=episode_id
    )
    
    memory3 = Memory(
        user_id="user_123",
        content="Unrelated memory",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.low(),
        episode_id="other_episode"
    )
    
    await db_client.create_memory(memory1)
    await db_client.create_memory(memory2)
    await db_client.create_memory(memory3)
    
    # Query by episode_id
    query = f"SELECT * FROM memory WHERE episode_id = '{episode_id}'"
    async with db_client.get_connection() as conn:
        result = await conn.query(query)
        
    if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
         records = result[0]['result']
    else:
         records = result
         
    assert len(records) == 2
    for record in records:
        assert record['episode_id'] == episode_id

@pytest.mark.asyncio
async def test_metacognitive_indexing(db_client):
    """Verify storage and filtering by confidence."""
    high_conf_mem = Memory(
        user_id="user_123",
        content="I am very sure about this",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.high(),
        confidence=0.95
    )
    
    low_conf_mem = Memory(
        user_id="user_123",
        content="I am not sure about this",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.low(),
        confidence=0.3
    )
    
    await db_client.create_memory(high_conf_mem)
    await db_client.create_memory(low_conf_mem)
    
    # Query high confidence memories
    query = "SELECT * FROM memory WHERE confidence > 0.8"
    async with db_client.get_connection() as conn:
        result = await conn.query(query)
        
    if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
         records = result[0]['result']
    else:
         records = result
         
    assert len(records) == 1
    assert records[0]['content'] == "I am very sure about this"
    assert records[0]['confidence'] == 0.95

@pytest.mark.asyncio
async def test_source_reliability(db_client):
    """Verify storage and filtering by source_reliability."""
    reliable_mem = Memory(
        user_id="user_123",
        content="Fact from trusted source",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.high(),
        source_reliability=0.99
    )
    
    unreliable_mem = Memory(
        user_id="user_123",
        content="Rumor from unknown source",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.low(),
        source_reliability=0.1
    )
    
    await db_client.create_memory(reliable_mem)
    await db_client.create_memory(unreliable_mem)
    
    # Query reliable memories
    query = "SELECT * FROM memory WHERE source_reliability > 0.9"
    async with db_client.get_connection() as conn:
        result = await conn.query(query)
        
    if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
         records = result[0]['result']
    else:
         records = result
         
    assert len(records) == 1
    assert records[0]['content'] == "Fact from trusted source"
    assert records[0]['source_reliability'] == 0.99
