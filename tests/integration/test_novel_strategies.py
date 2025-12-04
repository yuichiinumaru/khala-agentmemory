import sys
from unittest.mock import MagicMock, AsyncMock, patch

# Mock surrealdb module BEFORE it is imported by khala
mock_surreal_module = MagicMock()
mock_surreal_module.AsyncSurreal = MagicMock
mock_surreal_module.Surreal = MagicMock
sys.modules["surrealdb"] = mock_surreal_module
sys.modules["surrealdb.data"] = MagicMock()
sys.modules["surrealdb.data.types"] = MagicMock()
sys.modules["surrealdb.data.types.geometry"] = MagicMock()

import pytest
import pytest_asyncio
import os
import json
import uuid

# Now we can import Khala modules
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.application.services.surprise_service import SurpriseService
from khala.application.services.curiosity_service import CuriosityService
from khala.application.services.approval_service import ApprovalService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore

class MockAsyncSurreal:
    def __init__(self, url):
        self.url = url

    async def connect(self):
        pass

    async def signin(self, credentials):
        pass

    async def use(self, namespace, database):
        pass

    async def query(self, query, params=None):
        params = params or {}
        if "CREATE" in query:
             return [{"status": "OK", "result": [{"id": params.get("id", "req:1")}]}]
        elif "SELECT" in query:
             # Return mock data for curiosity
             if "memory" in query and "content" in query:
                 return [{"status": "OK", "result": [{"content": "Python is a programming language.", "confidence": 0.4}]}]
             if "approval_request" in query:
                 req_id = params.get("id", "req:1")
                 return [{"status": "OK", "result": [{"id": req_id, "status": "pending", "action": "delete_memory", "details": {"resource_id": "mem_1"}}]}]
             return [{"status": "OK", "result": []}]
        elif "UPDATE" in query:
             return [{"status": "OK", "result": []}]
        elif "DELETE" in query:
             return [{"status": "OK", "result": []}]
        return []

    async def close(self):
        pass

    async def subscribe_live(self, uuid):
        pass

    async def kill(self, uuid):
        pass

@pytest_asyncio.fixture
async def db_client():
    # Patch the AsyncSurreal class AND DatabaseSchema to avoid overhead
    with patch('khala.infrastructure.surrealdb.client.AsyncSurreal', side_effect=MockAsyncSurreal):
        with patch('khala.infrastructure.surrealdb.client.DatabaseSchema') as MockSchema:
            mock_schema_instance = MockSchema.return_value
            mock_schema_instance.create_schema = AsyncMock()

            client = SurrealDBClient(
                url="ws://mock",
                username="root",
                password="root",
                namespace="test",
                database="test"
            )
            await client.initialize()
            yield client
            await client.close()

@pytest.fixture
def mock_gemini():
    client = MagicMock(spec=GeminiClient)
    client.generate_text = AsyncMock()
    return client

@pytest.mark.asyncio
async def test_surprise_service(mock_gemini):
    service = SurpriseService(mock_gemini)

    # Mock response for high surprise
    mock_gemini.generate_text.return_value = {"content": "0.9"}

    memory = Memory(
        user_id="user_1",
        content="The sky is green.",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore.low()
    )

    context_memories = [
        Memory(user_id="user_1", content="The sky is blue.", tier=MemoryTier.LONG_TERM, importance=ImportanceScore.high())
    ]

    await service.process_memory_surprise(memory, context_memories)

    # Check if importance was boosted to 1.0 (SurpriseService logic)
    assert memory.importance.value == 1.0

    # Check metadata
    assert memory.metadata.get("surprise_detected") is True
    assert memory.metadata.get("surprise_score") == 0.9

@pytest.mark.asyncio
async def test_curiosity_service(mock_gemini, db_client):
    service = CuriosityService(mock_gemini, db_client)

    # Mock Gemini response
    mock_gemini.generate_text.return_value = {
        "content": '["What are Python decorators?", "How does GIL work?"]'
    }

    user_id = "user_curiosity"
    topic = "python"

    questions = await service.identify_knowledge_gaps(topic, user_id)

    assert len(questions) == 2
    assert "What are Python decorators?" in questions

    # Test low confidence
    mock_gemini.generate_text.return_value = {"content": "Is this true?"}
    questions_low = await service.generate_inquiry_for_low_confidence(user_id)
    assert len(questions_low) == 1
    assert "Is this true?" in questions_low

@pytest.mark.asyncio
async def test_approval_service(db_client):
    service = ApprovalService(db_client)

    req_id = await service.create_request("delete_memory", {"id": "mem_1"}, "agent_1")

    assert req_id is not None
    assert "approval_request" in req_id

    # Get request
    req = await service.get_request(req_id)
    assert req['action'] == "delete_memory"
    assert req['status'] == "pending"

    # Approve
    success = await service.approve(req_id, "admin")
    assert success is True
