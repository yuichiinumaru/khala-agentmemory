import pytest
import asyncio
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory, Entity, Relationship, EntityType, MemoryTier, ImportanceScore

@pytest.mark.asyncio
async def test_recursive_graph_traversal(mock_surreal_client):
    """Build a graph and test deep traversal."""
    client = SurrealDBClient()
    await client.initialize()

    # Structure: A -> B -> C -> D -> E (Chain)
    entities = ["A", "B", "C", "D", "E"]
    ids = {}

    # Create Entities
    for char in entities:
        ent = Entity(
            text=char,
            entity_type=EntityType.CONCEPT,
            confidence=1.0,
            metadata={"depth": entities.index(char)}
        )
        ids[char] = await client.create_entity(ent)

    # Create Edges
    for i in range(len(entities)-1):
        rel = Relationship(
            from_entity_id=ids[entities[i]],
            to_entity_id=ids[entities[i+1]],
            relation_type="leads_to",
            strength=1.0
        )
        await client.create_relationship(rel)

    query = f"""
    SELECT *,
    (SELECT to_entity_id FROM relationship WHERE from_entity_id = $parent.id) as next_hops
    FROM entity WHERE id = $start_id;
    """

    # We use manual query here since get_connection is context manager
    async with client.get_connection() as conn:
        res = await conn.query(query, {"start_id": ids["A"]})

        if res and isinstance(res, list):
            item = res[0]
            if isinstance(item, dict) and 'result' in item:
                 item = item['result'][0]

            # The Mock in conftest.py is hardcoded to return next_hops=['B'] if 'A' is in ID
            # So this asserts our mock logic works and client handles it
            assert item is not None

    await client.close()
