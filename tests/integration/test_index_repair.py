"""Integration test for Strategy 159 (Index Repair)."""

import pytest
import pytest_asyncio
import uuid
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.application.services.index_repair_service import IndexRepairService
from khala.infrastructure.background.jobs.index_repair_job import IndexRepairJob

@pytest.mark.asyncio
async def test_index_repair_service_scans_and_repairs():
    """Test that the service finds missing embeddings and repairs them."""

    # Mock clients
    mock_db = MagicMock(spec=SurrealDBClient)
    mock_gemini = MagicMock(spec=GeminiClient)

    # Setup mock connections
    mock_conn = AsyncMock()
    mock_db.get_connection.return_value.__aenter__.return_value = mock_conn

    # Service instance
    service = IndexRepairService(mock_db, mock_gemini)

    # 1. Mock finding missing embeddings
    # First query returns one record with missing embedding
    mock_record = {
        "id": "memory:test_123",
        "content": "Test content for repair"
    }

    # Configure mock query responses
    async def query_side_effect(query, params=None):
        if "embedding IS NONE" in query:
            return [{"result": [mock_record]}]
        if "array::len(embedding)" in query:
            return [{"result": []}] # No dimension mismatches
        return []

    mock_conn.query.side_effect = query_side_effect

    # 2. Mock generating embeddings
    expected_embedding = [0.1] * 768
    mock_gemini.generate_embeddings = AsyncMock(return_value=[expected_embedding])

    # 3. Mock updating memory
    mock_db.update_memory_field = AsyncMock()

    # Execute repair
    report = await service.scan_and_repair(fix=True)

    # Assertions
    assert report["scanned_count"] == 1
    assert report["issues_found"]["missing_embeddings"] == 1
    assert report["repaired_count"] == 1
    assert len(report["errors"]) == 0

    # Verify Gemini was called
    mock_gemini.generate_embeddings.assert_called_once_with(["Test content for repair"])

    # Verify DB update was called
    mock_db.update_memory_field.assert_any_call(
        memory_id="memory:test_123",
        field="embedding",
        value=expected_embedding
    )

    # Verify metadata update
    # We can check that update_memory_field was called twice (once for embedding, once for metadata)
    assert mock_db.update_memory_field.call_count == 2

@pytest.mark.asyncio
async def test_index_repair_job_execution():
    """Test the job wrapper execution."""

    mock_db = MagicMock(spec=SurrealDBClient)
    mock_gemini = MagicMock(spec=GeminiClient)

    with patch("khala.infrastructure.background.jobs.index_repair_job.IndexRepairService") as MockService:
        # Setup mock service
        mock_service_instance = MockService.return_value
        mock_service_instance.scan_and_repair = AsyncMock(return_value={"status": "success"})

        # Init job
        job = IndexRepairJob(mock_db, mock_gemini)

        # Execute
        result = await job.execute({"fix": True, "batch_size": 20})

        # Verify
        assert result == {"status": "success"}
        mock_service_instance.scan_and_repair.assert_called_once_with(
            fix=True, batch_size=20, scan_all=False
        )
