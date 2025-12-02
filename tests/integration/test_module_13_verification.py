import pytest
import pytest_asyncio
import os
import uuid
from datetime import datetime, timezone
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.surrealdb.schema import DatabaseSchema

# Use the same SurrealDB configuration
SURREALDB_URL = os.getenv("SURREALDB_URL", "ws://localhost:8001/rpc")
SURREAL_USER = "root"
SURREAL_PASS = "surrealdb_secret_password"
SURREAL_NS = "test_ns_mod13"
SURREAL_DB = "test_db_mod13"

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
        await conn.query("REMOVE TABLE reasoning_paths")
        await conn.query("REMOVE TABLE kg_embeddings")
        await conn.query("REMOVE TABLE latent_states")
        await conn.query("REMOVE TABLE hierarchical_coordination")
        await conn.query("REMOVE TABLE training_curves")

@pytest.mark.asyncio
async def test_lgkgr_tables(db_client):
    """Verify LGKGR tables (reasoning_paths, kg_embeddings)."""
    # Test reasoning_paths
    query_path = """
    CREATE reasoning_paths CONTENT {
        query_entity: 'EntityA',
        target_entity: 'EntityB',
        path: ['EntityA', 'Relation1', 'EntityB'],
        llm_explanation: 'Because A relates to B',
        confidence: 0.9,
        final_rank: 1,
        created_at: time::now()
    };
    """
    async with db_client.get_connection() as conn:
        result = await conn.query(query_path)
    
    # Check if created
    if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
         records = result[0]['result']
    else:
         records = result
    assert len(records) == 1
    assert records[0]['query_entity'] == 'EntityA'

    # Test kg_embeddings
    # Create a 768-dimension vector
    vector = [0.1] * 768
    query_emb = f"""
    CREATE kg_embeddings CONTENT {{
        entity_id: 'EntityA',
        embedding: {vector},
        task_context: 'search',
        representation_timestamp: time::now()
    }};
    """
    async with db_client.get_connection() as conn:
        result = await conn.query(query_emb)
        
    if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
         records = result[0]['result']
    else:
         records = result
    assert len(records) == 1
    assert records[0]['entity_id'] == 'EntityA'

@pytest.mark.asyncio
async def test_latent_mas_tables(db_client):
    """Verify LatentMAS tables (latent_states)."""
    query = """
    CREATE latent_states CONTENT {
        agent_id: 'Agent007',
        iteration: 1,
        state_embedding: [0.5, 0.5],
        decision_made: 'explore',
        created_at: time::now()
    };
    """
    async with db_client.get_connection() as conn:
        result = await conn.query(query)
        
    if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
         records = result[0]['result']
    else:
         records = result
    assert len(records) == 1
    assert records[0]['agent_id'] == 'Agent007'

@pytest.mark.asyncio
async def test_fulora_tables(db_client):
    """Verify FULORA tables (hierarchical_coordination)."""
    query = """
    CREATE hierarchical_coordination CONTENT {
        from_decision: 'ManagerDecision',
        to_action: 'WorkerAction',
        guidance_type: 'directive',
        created_at: time::now()
    };
    """
    async with db_client.get_connection() as conn:
        result = await conn.query(query)
        
    if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
         records = result[0]['result']
    else:
         records = result
    assert len(records) == 1
    assert records[0]['guidance_type'] == 'directive'

@pytest.mark.asyncio
async def test_marsrl_tables(db_client):
    """Verify MarsRL tables (training_curves)."""
    query = """
    CREATE training_curves CONTENT {
        model_id: 'ModelX',
        epoch: 10,
        loss: 0.05,
        accuracy: 0.98,
        reward_mean: 10.5,
        created_at: time::now()
    };
    """
    async with db_client.get_connection() as conn:
        result = await conn.query(query)
        
    if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
         records = result[0]['result']
    else:
         records = result
    assert len(records) == 1
    assert records[0]['accuracy'] == 0.98
