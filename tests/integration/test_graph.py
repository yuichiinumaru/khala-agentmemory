"""Integration tests for Graph Weight Updates."""

import pytest
import pytest_asyncio
from unittest.mock import MagicMock, AsyncMock
from khala.infrastructure.surrealdb.client import SurrealDBClient

class TestGraphWeightUpdates:
    """Test suite for Graph Weight Updates."""

    @pytest_asyncio.fixture
    async def mock_client(self):
        """Mock SurrealDB client."""
        client = MagicMock(spec=SurrealDBClient)
        client.get_connection = MagicMock()
        client.update_relationship_weight = AsyncMock()
        return client

    @pytest.mark.asyncio
    async def test_update_relationship_weight_mock(self, mock_client):
        """Test weight update with mocked client."""
        relationship_id = "rel_123"
        new_weight = 0.85

        # Call the method
        await mock_client.update_relationship_weight(relationship_id, new_weight)

        # Verify call
        mock_client.update_relationship_weight.assert_called_once_with(relationship_id, new_weight)
