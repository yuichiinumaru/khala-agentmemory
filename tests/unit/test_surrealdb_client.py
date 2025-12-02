"""Unit tests for SurrealDB client.

Following TDD principles, these tests verify the database operations
and connection management functionality.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, patch, MagicMock

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory, Entity, Relationship
from khala.domain.memory.value_objects import EmbeddingVector, ImportanceScore, MemoryTier


class TestSurrealDBClient:
    """Test cases for SurrealDB client."""
    
    @pytest.fixture
    def client(self):
        """Create a test client."""
        return SurrealDBClient(
            url="ws://localhost:8000/rpc",
            namespace="test_khala",
            database="test_memories",
            username="test_user",
            password="test_pass"
        )
    
    @pytest.mark.asyncio
    async def test_client_initialization(self, client):
        """Test client initialization parameters."""
        assert client.url == "ws://localhost:8000/rpc"
        assert client.namespace == "test_khala"
        assert client.database == "test_memories"
        assert client.username == "test_user"
        assert client.password == "test_pass"
        assert client.max_connections == 10
        assert not client._initialized
    
    @pytest.mark.asyncio
    async def test_connection_pool_management(self, client):
        """Test connection pool management."""
        # Mock the Surreal connection
        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_surreal.return_value = mock_conn
            
            # Initialize client
            await client.initialize()
            
            assert client._initialized
            assert len(client._connection_pool) == 1
            mock_conn.connect.assert_called_once()
            mock_conn.signin.assert_called_once_with({
                "username": "test_user", 
                "password": "test_pass"
            })
    
    @pytest.mark.asyncio
    async def test_get_connection_context_manager(self, client):
        """Test connection context manager."""
        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_surreal.return_value = mock_conn
            
            await client.initialize()
            
            async with client.get_connection() as conn:
                assert conn == mock_conn
            
            # Connection should be returned to pool
            assert len(client._connection_pool) == 1
    
    @pytest.mark.asyncio
    async def test_create_memory(self, client):
        """Test creating a memory record."""
        # Setup memory
        embedding = EmbeddingVector([0.1] * 768)
        memory = Memory(
            user_id="user123",
            content="Test memory content",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.high(),
            embedding=embedding,
            tags=["test", "example"]
        )
        
        # Mock database connection
        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()

            async def query_side_effect(query, params=None):
                if "SELECT id FROM memory" in query and "content_hash" in query:
                    return [] # No duplicate
                if "CREATE" in query:
                    return [{"id": memory.id}]
                return [] # Default
            def query_side_effect(query, params=None):
                if "SELECT id FROM memory" in query:
                    return []
                if "CREATE" in query and "memory" in query:
                    return [{"id": memory.id}]
                return []

            mock_conn.query.side_effect = query_side_effect
            mock_surreal.return_value = mock_conn
            # Side effect needs to account for schema initialization queries first
            # Schema initialization queries happen in client.initialize() called by get_connection()
            # But here we assume initialize() might be mocked or we provide enough side effects
            
            # Since client.initialize() calls DatabaseSchema.create_schema() which makes many calls,
            # we should mock DatabaseSchema to avoid that complexity in this unit test.
            with patch('khala.infrastructure.surrealdb.client.DatabaseSchema') as MockSchema:
                mock_schema_instance = MockSchema.return_value
                mock_schema_instance.create_schema = AsyncMock()

                # Now side effects only apply to logic inside create_memory
                mock_conn.query.side_effect = [
                    [],  # First call: Check for duplicate (return empty)
                    [{"id": memory.id}] # Second call: Create (return new ID)
                ]
                mock_surreal.return_value = mock_conn

                async with client.get_connection() as conn:
                    result = await client.create_memory(memory)
            
            assert result == memory.id
            
            # Find the create call
            create_call = None
            for call in mock_conn.query.call_args_list:
                args = call[0]
                # call is (args, kwargs)
                q = args[0]
                p = args[1] if len(args) > 1 else {}
                if "CREATE" in q and "memory" in q:
                    create_call = (q, p)
                    break

            assert create_call is not None, "Create query not found in calls"
            query, params = create_call

            assert params["user_id"] == memory.user_id
            assert params["content"] == memory.content
            assert params["tier"] == memory.tier.value
            assert params["embedding"] == embedding.values
    
    @pytest.mark.asyncio
    async def test_get_memory_not_found(self, client):
        """Test getting a memory that doesn't exist."""
        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_conn.query.return_value = []  # Empty result
            mock_surreal.return_value = mock_conn
            
            result = await client.get_memory("nonexistent_id")
            assert result is None
    
    @pytest.mark.asyncio
    async def test_search_memories_by_vector(self, client):
        """Test vector similarity search."""
        embedding = EmbeddingVector([0.1] * 768)
        
        # Mock search results
        mock_results = [
            {
                "id": "mem1",
                "content": "Similar memory",
                "similarity": 0.95
            },
            {
                "id": "mem2", 
                "content": "Another similar",
                "similarity": 0.87
            }
        ]
        
        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_conn.query.return_value = mock_results
            mock_surreal.return_value = mock_conn
            
            results = await client.search_memories_by_vector(
                embedding, "user123", top_k=5
            )
        
        assert len(results) == 2
        assert results[0]["id"] == "mem1"
        
        # Verify query parameters - find search query
        search_call = None
        for call in mock_conn.query.call_args_list:
            args = call[0]
            q = args[0]
            p = args[1] if len(args) > 1 else {}
            if "SELECT" in q and "vector::similarity" in q:
                search_call = (q, p)
                break

        assert search_call is not None
        query, params = search_call
        
        assert params["user_id"] == "user123"
        assert params["embedding"] == embedding.values
        assert params["top_k"] == 5
        assert params["min_similarity"] == 0.6
    
    @pytest.mark.asyncio
    async def test_search_memories_by_bm25(self, client):
        """Test BM25 full-text search."""
        mock_results = [
            {
                "id": "mem1",
                "content": "Python programming tutorial"
            },
            {
                "id": "mem2",
                "content": "Python data science guide"
            }
        ]
        
        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_conn.query.return_value = mock_results
            mock_surreal.return_value = mock_conn
            
            results = await client.search_memories_by_bm25(
                "Python tutorial", "user123"
            )
        
        assert len(results) == 2
        assert "Python" in results[0]["content"]
        
        # Verify query parameters
        search_call = None
        for call in mock_conn.query.call_args_list:
            args = call[0]
            q = args[0]
            p = args[1] if len(args) > 1 else {}
            if "SELECT" in q and "content @@ $query_text" in q:
                search_call = (q, p)
                break

        assert search_call is not None
        query, params = search_call

        assert params["user_id"] == "user123"
        assert params["query_text"] == "Python tutorial"
    
    @pytest.mark.asyncio
    async def test_search_memories_by_location(self, client):
        """Test geospatial search."""
        mock_results = [
            {
                "id": "mem1",
                "content": "Near memory",
                "distance": 100.0 # meters
            }
        ]

        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_conn.query.return_value = mock_results
            mock_surreal.return_value = mock_conn

            results = await client.search_memories_by_location(
                location={"lat": 40.7, "lon": -74.0},
                radius_km=10.0,
                user_id="user123"
            )

        assert len(results) == 1
        assert results[0]["id"] == "mem1"

        # Verify query parameters
        search_call = None
        for call in mock_conn.query.call_args_list:
            args = call[0]
            q = args[0]
            p = args[1] if len(args) > 1 else {}
            if "SELECT" in q and "geo::distance" in q:
                search_call = (q, p)
                break

        assert search_call is not None
        query, params = search_call

        assert params["user_id"] == "user123"
        assert params["radius_m"] == 10000.0
        assert params["point"]["coordinates"] == [-74.0, 40.7]

    @pytest.mark.asyncio
    async def test_get_memories_by_tier(self, client):
        """Test getting memories by tier."""
        # Mock database response
        mock_db_results = [
            {
                "id": "mem1",
                "user_id": "user123",
                "content": "Working memory 1",
                "tier": "working",
                "importance": 0.75,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "accessed_at": datetime.now(timezone.utc).isoformat(),
                "access_count": 5,
                "tags": ["test"],
                "verification_score": 0.8,
                "is_archived": False,
            }
        ]
        
        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_conn.query.return_value = mock_db_results
            mock_surreal.return_value = mock_conn
            
            memories = await client.get_memories_by_tier(
                "user123", "working"
            )
        
        assert len(memories) == 1
        memory = memories[0]
        assert memory.user_id == "user123"
        assert memory.tier == MemoryTier.WORKING
        assert memory.importance.value == 0.75
    
    @pytest.mark.asyncio
    async def test_update_memory(self, client):
        """Test updating an existing memory."""
        memory = Memory(
            user_id="user123",
            content="Updated content",
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.medium()
        )
        memory.add_keyword_tag("updated")
        
        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_conn.query.return_value = [{"id": memory.id}]
            mock_surreal.return_value = mock_conn
            
            async with client.get_connection() as conn:
                await client.update_memory(memory)
            
            # Verify update query
            update_call = None
            for call in mock_conn.query.call_args_list:
                args = call[0]
                q = args[0]
                p = args[1] if len(args) > 1 else {}
                if "UPDATE" in q and "CONTENT" in q:
                    update_call = (q, p)
                    break
            
            assert update_call is not None
            query, params = update_call

            assert params["id"] == memory.id
            assert params["content"] == "Updated content"
            assert "updated" in params["tags"]
    
    @pytest.mark.asyncio
    async def test_delete_memory(self, client):
        """Test deleting a memory."""
        with patch('khala.infrastructure.surrealdb.client.AsyncSurreal') as mock_surreal:
            mock_conn = AsyncMock()
            mock_conn.query.return_value = []
            mock_surreal.return_value = mock_conn
            
            await client.delete_memory("mem123")
            
            # Verify delete query
            delete_call = None
            for call in mock_conn.query.call_args_list:
                args = call[0]
                q = args[0]
                p = args[1] if len(args) > 1 else {}
                if "DELETE" in q and "memory" in q:
                    delete_call = (q, p)
                    break
            
            assert delete_call is not None
            query, params = delete_call

            assert "DELETE" in query and "type::thing('memory', $id)" in query
            assert params["id"] == "mem123"
    
    @pytest.mark.asyncio
    async def test_close_connections(self, client):
        """Test closing all connections."""
        # Add some mock connections to pool
        mock_conn1 = AsyncMock()
        mock_conn2 = AsyncMock()
        client._connection_pool = [mock_conn1, mock_conn2]
        client._initialized = True
        
        await client.close()
        
        assert len(client._connection_pool) == 0
        assert not client._initialized
        mock_conn1.close.assert_called_once()
        mock_conn2.close.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_deserialize_memory(self, client):
        """Test memory deserialization from database record."""
        from khala.domain.memory.entities import Memory
        
        # Create test data
        test_data = {
            "id": "test_memory_id",
            "user_id": "user123",
            "content": "Test memory content",
            "tier": "working",
            "importance": 0.75,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "accessed_at": datetime.now(timezone.utc).isoformat(),
            "access_count": 3,
            "tags": ["test", "example"],
            "verification_score": 0.85,
            "is_archived": False,
        }
        
        # Test deserialization
        memory = client._deserialize_memory(test_data)
        
        assert memory.id == "test_memory_id"
        assert memory.user_id == "user123"
        assert memory.content == "Test memory content"
        assert memory.tier == MemoryTier.WORKING
        assert memory.importance.value == 0.75
        assert memory.access_count == 3
        assert memory.tags == ["test", "example"]
        assert memory.verification_score == 0.85
        assert not memory.is_archived
