import sys
from unittest.mock import MagicMock, AsyncMock, patch
import pytest
import asyncio
import random
import string

# Mock surrealdb module BEFORE it is imported by khala
# This handles the top-level import in client.py
mock_surreal_module = MagicMock()
mock_surreal_module.AsyncSurreal = MagicMock
mock_surreal_module.Surreal = MagicMock
sys.modules["surrealdb"] = mock_surreal_module

def random_string(length=10):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

class MockAsyncSurreal:
    def __init__(self, url):
        self.url = url
        self._data = {} # Simple in-memory storage for basics

    async def connect(self):
        await asyncio.sleep(0.001)

    async def signin(self, credentials):
        pass

    async def use(self, namespace, database):
        pass

    async def query(self, query, params=None):
        await asyncio.sleep(0.001)
        params = params or {}

        # Basic parsing logic for Mocks
        if "CREATE" in query:
             # Extract ID if provided or generate
             oid = params.get("id", f"memory:{random_string()}")
             return [{"status": "OK", "result": [{"id": oid}]}]

        elif "SELECT" in query:
            if "count()" in query.lower():
                 return [{"status": "OK", "result": [{"count": 0}]}]

            # Return a generic mock record based on context
            res = [{
                "id": params.get("id", "mock_id"),
                "user_id": params.get("user_id", "mock_user"),
                "content": "Mock Content",
                "tier": "working",
                "importance": 0.5,
                "created_at": "2024-01-01T00:00:00Z",
                "updated_at": "2024-01-01T00:00:00Z",
                "accessed_at": "2024-01-01T00:00:00Z",
                "access_count": 0,
                "verification_status": "pending",
                "is_archived": False,
                "metadata": {},
                "tags": [],
                "next_hops": ["B"] if "A" in str(params.get("id")) else [] # For graph test
            }]
            return [{"status": "OK", "result": res}]

        elif "UPDATE" in query:
             return [{"status": "OK", "result": []}]

        elif "DELETE" in query:
             return [{"status": "OK", "result": []}]

        return []

    async def close(self):
        pass

@pytest.fixture
def mock_surreal_client():
    """Fixture that mocks the AsyncSurreal class within the client module."""
    # We patch the class where it is used/imported in the client module
    with patch('khala.infrastructure.surrealdb.client.AsyncSurreal', side_effect=MockAsyncSurreal):
        yield

@pytest.fixture
def event_loop():
    """Create an instance of the default event loop for each test case."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()
