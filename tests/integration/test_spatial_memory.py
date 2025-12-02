import pytest
import pytest_asyncio
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.application.services.spatial_memory_service import SpatialMemoryService
from khala.domain.memory.value_objects import Location
import time

@pytest_asyncio.fixture
async def db_client():
    client = SurrealDBClient()
    await client.initialize()

    # Reset schema/data to ensure clean state
    try:
        async with client.get_connection() as conn:
            await conn.query("DELETE FROM memory;")
    except Exception as e:
        print(f"Cleanup warning: {e}")

    yield client

    # Final cleanup
    try:
        async with client.get_connection() as conn:
            await conn.query("DELETE FROM memory;")
    except Exception:
        pass
    # await client.close() - if client had a close method exposed or context manager usage

@pytest_asyncio.fixture
async def spatial_service(db_client):
    return SpatialMemoryService(db_client)

@pytest.mark.asyncio
async def test_spatial_memory_workflow(spatial_service, db_client):
    """Test the full spatial memory workflow (Strategies 111-115)."""

    # 1. Create memories with locations
    from khala.domain.memory.entities import Memory
    from khala.domain.memory.value_objects import MemoryTier, ImportanceScore

    # Memory 1: Paris (Eiffel Tower)
    mem1 = Memory(
        content="Eiffel Tower visit",
        user_id="user_spatial_test",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        metadata={"city": "Paris"}
    )
    # create_memory returns the actual ID (handling deduplication)
    mem1_id = await db_client.create_memory(mem1)

    # Memory 2: Paris (Louvre) - ~3km from Eiffel Tower
    mem2 = Memory(
        content="Louvre Museum art",
        user_id="user_spatial_test",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        metadata={"city": "Paris"}
    )
    mem2_id = await db_client.create_memory(mem2)

    # Memory 3: London (Big Ben) - ~340km from Paris
    mem3 = Memory(
        content="Big Ben clock",
        user_id="user_spatial_test",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        metadata={"city": "London"}
    )
    mem3_id = await db_client.create_memory(mem3)

    # Update locations
    # Paris, Eiffel: 48.8584° N, 2.2945° E
    res1 = await spatial_service.update_memory_location(mem1_id, 48.8584, 2.2945)
    print(f"Update mem1 result: {res1}")

    # Paris, Louvre: 48.8606° N, 2.3376° E
    res2 = await spatial_service.update_memory_location(mem2_id, 48.8606, 2.3376)
    print(f"Update mem2 result: {res2}")

    # London, Big Ben: 51.5007° N, 0.1246° W
    res3 = await spatial_service.update_memory_location(mem3_id, 51.5007, -0.1246)
    print(f"Update mem3 result: {res3}")

    # Verify updates
    m1 = await db_client.get_memory(mem1_id)
    print(f"Mem1 location: {m1.location if m1 else 'None'}")

    # Wait for indexing/persistence if needed (SurrealDB is usually immediate but good for safety)

    # 2. Test Proximity Search (Strategy 112)
    # Search near Eiffel Tower (radius 5km) -> Should find Eiffel + Louvre, exclude London
    nearby = await spatial_service.find_nearby_memories(
        latitude=48.8584,
        longitude=2.2945,
        max_distance_km=5.0
    )

    print(f"Nearby memories: {len(nearby)}")
    print(f"Nearby data: {nearby}")

    assert len(nearby) == 2
    # Handle RecordID objects
    ids = [str(m['id']).split(':')[-1] for m in nearby]
    assert mem1.id in ids
    assert mem2.id in ids
    assert mem3.id not in ids

    # Search near London -> Should find Big Ben
    nearby_london = await spatial_service.find_nearby_memories(
        latitude=51.5007,
        longitude=-0.1246,
        max_distance_km=10.0
    )
    assert len(nearby_london) == 1
    assert str(nearby_london[0]['id']).split(':')[-1] == mem3.id

    # 3. Test Region Query (Strategy 113)
    # Define polygon around Paris
    paris_polygon = [
        (2.2, 48.8), (2.4, 48.8), (2.4, 48.9), (2.2, 48.9), (2.2, 48.8)
    ]

    in_region = await spatial_service.find_within_region(paris_polygon)
    assert len(in_region) >= 2 # Might pick up previous test runs if db not cleared, but at least ours
    # Handle RecordID objects
    region_ids = [str(m['id']).split(':')[-1] for m in in_region]
    assert mem1.id in region_ids
    assert mem2.id in region_ids
    assert mem3.id not in region_ids

    # 4. Test Trajectory (Strategy 114)
    # Move Memory 1 slightly
    await spatial_service.update_memory_location(mem1_id, 48.8590, 2.2950)

    trajectory = await spatial_service.get_memory_trajectory(mem1_id)

    # Check if current location is included in trajectory (get_memory_trajectory implementation includes current)
    # logic: trajectory.append({"source": "current", ...})
    # If versions empty, at least current should be there?

    assert len(trajectory) >= 1
    # Check if location is GeometryPoint (from current) or dict (from history)
    loc = trajectory[0]['location']
    if hasattr(loc, 'longitude'):
        assert loc.longitude == 2.2950
        assert loc.latitude == 48.8590
    else:
        # dict fallback (history might be serialized as dict if not using _deserialize)
        assert loc['coordinates'] == [2.2950, 48.8590]

    # 5. Test Clustering (Strategy 115)
    clusters = await spatial_service.find_spatial_clusters(grid_precision=4)
    assert len(clusters) > 0
    # Paris memories should form a cluster

    # Cleanup
    await db_client.delete_memory(mem1.id)
    await db_client.delete_memory(mem2.id)
    await db_client.delete_memory(mem3.id)

if __name__ == "__main__":
    # Setup loop for manual run if needed
    import asyncio
    asyncio.run(test_spatial_memory_workflow())
