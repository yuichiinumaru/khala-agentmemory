import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from khala.application.services.explainability_service import ExplainabilityService
from khala.infrastructure.surrealdb.client import SurrealDBClient

@pytest.mark.asyncio
class TestExplainabilityService:
    async def test_store_reasoning_trace(self):
        mock_client = Mock(spec=SurrealDBClient)
        # Mock get_connection to return an async context manager
        mock_conn = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        mock_client.get_connection.return_value = mock_ctx

        mock_conn.create.return_value = {"id": "reasoning_paths:123"}

        service = ExplainabilityService(mock_client)
        trace_id = await service.store_reasoning_trace(
            query_entity="Q1",
            target_entity="T1",
            path=["Step 1", "Step 2"],
            llm_explanation="Because...",
            confidence=0.9,
            final_rank=1
        )

        assert trace_id == "reasoning_paths:123"
        mock_conn.create.assert_called_once()
        args, _ = mock_conn.create.call_args
        assert args[0] == "reasoning_paths"
        assert args[1]["query_entity"] == "Q1"

    async def test_get_trace_as_graph(self):
        mock_client = Mock(spec=SurrealDBClient)
        mock_conn = AsyncMock()
        mock_ctx = AsyncMock()
        mock_ctx.__aenter__.return_value = mock_conn
        mock_ctx.__aexit__.return_value = None
        mock_client.get_connection.return_value = mock_ctx

        mock_trace = {
            "id": "reasoning_paths:123",
            "query_entity": "Q1",
            "target_entity": "T1",
            "path": ["Step 1", "Step 2"],
            "llm_explanation": "Because...",
            "confidence": 0.9
        }
        mock_conn.select.return_value = mock_trace

        service = ExplainabilityService(mock_client)
        result = await service.get_trace_as_graph("reasoning_paths:123")

        assert result["trace_id"] == "reasoning_paths:123"
        assert "graph" in result
        nodes = result["graph"]["nodes"]
        edges = result["graph"]["edges"]

        # Start + 2 steps + End = 4 nodes
        assert len(nodes) == 4
        # 3 edges connecting them
        assert len(edges) == 3

        assert nodes[0]["id"] == "start"
        assert nodes[-1]["id"] == "end"
        assert edges[0]["from"] == "start"
        assert edges[-1]["to"] == "end"
