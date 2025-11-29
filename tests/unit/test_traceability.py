"""
Test suite for Information Traceability (Module 7).
Verifies that Source and Sentiment metadata are correctly persisted and retrieved.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch
from dataclasses import asdict

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory
from khala.domain.memory.value_objects import ImportanceScore, MemoryTier, MemorySource, Sentiment

class TestTraceability:
    """Test cases for memory traceability and sentiment."""

    @pytest.fixture
    def client(self):
        """Create a test client."""
        return SurrealDBClient(
            url="ws://localhost:8000/rpc",
            namespace="test_khala",
            database="test_memories"
        )

    @pytest.mark.asyncio
    async def test_create_memory_with_source(self, client):
        """Test creating a memory with source information."""
        source_time = datetime.now(timezone.utc)
        source = MemorySource(
            source_type="user_input",
            source_id="msg_123",
            location="chat_window",
            timestamp=source_time,
            confidence=0.95
        )

        memory = Memory(
            user_id="user123",
            content="Traceable memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium(),
            source=source
        )

        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_conn.query.return_value = [{"id": memory.id}]
            mock_surreal.return_value = mock_conn

            await client.create_memory(memory)

            # Verify create call parameters
            create_call = None
            for call in mock_conn.query.call_args_list:
                args = call[0]
                q = args[0]
                p = args[1] if len(args) > 1 else {}
                if "CREATE type::thing('memory'" in q:
                    create_call = (q, p)
                    break

            assert create_call is not None
            _, params = create_call

            assert params["source"] is not None
            assert params["source"]["source_type"] == "user_input"
            assert params["source"]["source_id"] == "msg_123"
            assert params["source"]["timestamp"] == source_time.isoformat()

    @pytest.mark.asyncio
    async def test_create_memory_with_sentiment(self, client):
        """Test creating a memory with sentiment information."""
        sentiment = Sentiment(
            score=0.8,
            label="positive",
            emotions={"joy": 0.9, "trust": 0.7}
        )

        memory = Memory(
            user_id="user123",
            content="Happy memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium(),
            sentiment=sentiment
        )

        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_conn.query.return_value = [{"id": memory.id}]
            mock_surreal.return_value = mock_conn

            await client.create_memory(memory)

            # Verify create call parameters
            create_call = None
            for call in mock_conn.query.call_args_list:
                args = call[0]
                q = args[0]
                p = args[1] if len(args) > 1 else {}
                if "CREATE type::thing('memory'" in q:
                    create_call = (q, p)
                    break

            assert create_call is not None
            _, params = create_call

            assert params["sentiment"] is not None
            assert params["sentiment"]["score"] == 0.8
            assert params["sentiment"]["label"] == "positive"
            assert params["sentiment"]["emotions"]["joy"] == 0.9

    @pytest.mark.asyncio
    async def test_deserialize_memory_with_traceability(self, client):
        """Test deserializing memory with source and sentiment."""
        source_time = datetime.now(timezone.utc)
        # Use microsecond=0 because isoformat might include it but we want to ensure comparison works if lost or kept
        source_time = source_time.replace(microsecond=0)

        test_data = {
            "id": "mem_trace_1",
            "user_id": "user123",
            "content": "Traceable content",
            "tier": "working",
            "importance": 0.5,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "source": {
                "source_type": "document",
                "source_id": "doc_1",
                "location": "page_5",
                "timestamp": source_time.isoformat(),
                "confidence": 0.8
            },
            "sentiment": {
                "score": -0.5,
                "label": "negative",
                "emotions": {"anger": 0.6}
            }
        }

        memory = client._deserialize_memory(test_data)

        assert memory.source is not None
        assert memory.source.source_type == "document"
        assert memory.source.source_id == "doc_1"
        assert memory.source.timestamp.replace(tzinfo=timezone.utc) == source_time.replace(tzinfo=timezone.utc)

        assert memory.sentiment is not None
        assert memory.sentiment.score == -0.5
        assert memory.sentiment.label == "negative"
        assert memory.sentiment.emotions["anger"] == 0.6
