
import pytest
import pytest_asyncio
import asyncio
import os
from datetime import datetime, timezone

from khala.domain.sop.services import SOPRegistry
from khala.domain.sop.entities import SOP, SOPStep
from khala.infrastructure.persistence.repositories.sop_repository import SurrealSOPRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient, SurrealConfig
from khala.infrastructure.surrealdb.schema import DatabaseSchema

@pytest_asyncio.fixture
async def db_client():
    """Setup DB client and schema."""
    config = SurrealConfig(
        url=os.getenv("SURREAL_URL", "ws://localhost:8000/rpc"),
        username=os.getenv("SURREAL_USER", "root"),
        password=os.getenv("SURREAL_PASS", "root"),
        namespace="test_ns",
        database="test_db"
    )
    client = SurrealDBClient(config)
    try:
        await client.initialize()
        schema = DatabaseSchema(client)
        await schema.create_schema() # Ensure SOP table exists
        yield client
    finally:
        # Cleanup
        try:
            await schema.drop_schema()
        except:
            pass
        await client.close()

@pytest.mark.asyncio
async def test_sop_persistence_success(db_client):
    """
    Test that SOPs ARE persisted to the DB and survive service recreation.
    """
    repo = SurrealSOPRepository(db_client)
    registry = SOPRegistry(repo)

    sop = SOP(
        id="sop:test_001", # SurrealDB ID format
        title="Test SOP",
        objective="Verify persistence",
        steps=[SOPStep(order=1, description="Step 1", expected_output="Output 1")],
        owner_role="tester",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc)
    )

    # Register (Async/DB)
    await registry.register_sop(sop)

    # Verify it exists
    fetched = await registry.get_sop("sop:test_001")
    assert fetched is not None
    assert fetched.title == "Test SOP"

    # Simulate "Restart" -> New Service, New Repo instance
    # (Same DB client to represent persistent storage)
    new_repo = SurrealSOPRepository(db_client)
    new_registry = SOPRegistry(new_repo)

    # Verify it's still there
    fetched_again = await new_registry.get_sop("sop:test_001")

    assert fetched_again is not None
    assert fetched_again.id == "sop:test_001"
    assert fetched_again.steps[0].description == "Step 1"
