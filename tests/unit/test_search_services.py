"""Unit tests for search domain services.

Following TDD principles, these tests verify the business logic
for search services and optimization strategies.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta
import numpy as np

from khala.domain.search.services import HybridSearchService, IntentClassifier, SignificanceScorer
from khala.domain.search.value_objects import Query, SearchResult, SearchIntent, SearchPipeline
from khala.domain.memory.entities import Memory, MemoryTier
from khala.domain.memory.value_objects import EmbeddingVector, ImportanceScore


class TestHybridSearchService:
    """Test cases for HybridSearchService."""
    
    @pytest.fixture
    def mock_memory_repo(self):
        """Mock memory repository."""
        return AsyncMock()
    
    @pytest.fixture
    def mock_entity_repo(self):
        """Mock entity repository."""
        return AsyncMock()
    
    @pytest.fixture
    def service(self, mock_memory_repo, mock_entity_repo):
        """Create service with mocked repositories."""
        return HybridSearchService(mock_memory_repo, mock_entity_repo)
    
    @pytest.fixture
    def sample_query(self):
        """Create a sample query."""
        embedding = np.array([0.1] * 768)
        return Query(
            text="Python programming tutorial",
            intent=SearchIntent.LEARNING,
            embedding=embedding,
            user_id="user123"
        )
    
    @pytest.mark.asyncio
    async def test_search_with_default_pipeline(self, service, sample_query):
        """Test search with default pipeline configuration."""
        # Mock repository responses
        service.memory_repository.search_by_vector.return_value = [
            {"id": "mem1", "content": "Python tutorial", "similarity": 0.85}
        ]
        service.memory_repository.search_by_text.return_value = [
            {"id": "mem2", "content": "Programming guide", "relevance": 0.75}
        ]
        
        # Execute search
        session = await service.search(sample_query)
        
        # Verify session
        assert session.user_id == "user123"
        assert session.is_completed()
        assert session.search_time_ms > 0
        assert len(session.results) > 0
        assert session.total_searched > 0
    
    @pytest.mark.asyncio
    async def test_search_with_custom_pipeline(self, service, sample_query):
        """Test search with custom pipeline configuration."""
        custom_pipeline = SearchPipeline(
            vector_enabled=True,
            bm25_enabled=False,  # Only vector search
            graph_traversal=False
        )
        
        # Mock vector search result
        service.memory_repository.search_by_vector.return_value = [
            {"id": "mem1", "content": "Vector result", "similarity": 0.9}
        ]
        
        session = await service.search(sample_query, custom_pipeline)
        
        # Verify only vector search was called
        service.memory_repository.search_by_vector.assert_called_once()
        service.memory_repository.search_by_text.assert_not_called()
    
    @pytest.mark.asyncio
    async def test_vector_search_execution(self, service, sample_query):
        """Test vector search execution."""
        embedding = EmbeddingVector([0.1] * 768)
        query_with_embedding = Query(
            text="test",
            intent=SearchIntent.FACTUAL,
            embedding=embedding.values,
            user_id="user123"
        )
        
        # Mock vector search
        service.memory_repository.search_by_vector.return_value = [
            {"id": "mem1", "content": "Similar memory", "similarity": 0.92}
        ]
        
        results = await service._vector_search(query_with_embedding, top_k=10)
        
        assert len(results) == 1
        result = results[0]
        assert result.memory_id == "mem1"
        assert result.confidence == 0.92
        assert "vector_similarity" in result.reasons
        
        # Verify repository call
        service.memory_repository.search_by_vector.assert_called_once_with(
            embedding, "user123", 10, min_similarity=0.6
        )
    
    @pytest.mark.asyncio
    async def test_bm25_search_execution(self, service, sample_query):
        """Test BM25 search execution."""
        # Mock text search
        service.memory_repository.search_by_text.return_value = [
            {"id": "mem2", "content": "Text matching result", "relevance": 0.78}
        ]
        
        results = await service._bm25_search(sample_query, top_k=10)
        
        assert len(results) == 1
        result = results[0]
        assert result.memory_id == "mem2"
        assert result.confidence == 0.78
        assert "text_relevance" in result.reasons
        
        # Verify repository call
        service.memory_repository.search_by_text.assert_called_once_with(
            "Python programming tutorial", "user123", 10
        )
    
    @pytest.mark.asyncio
    async def test_metadata_filtering(self, service):
        """Test metadata filtering functionality."""
        results = [
            SearchResult.create(
                memory_id="mem1",
                content="Result 1",
                confidence=0.8,
                metadata={"tier": "working", "access_count": 5}
            ),
            SearchResult.create(
                memory_id="mem2",
                content="Result 2", 
                confidence=0.7,
                metadata={"tier": "long_term", "access_count": 15}
            ),
            SearchResult.create(
                memory_id="mem3",
                content="Result 3",
                confidence=0.6,
                metadata={"tier": "working", "access_count": 8}
            )
        ]
        
        # Filter for working tier only
        filters = {"tier": "working"}
        filtered_results = await service._apply_metadata_filters(results, filters)
        
        assert len(filtered_results) == 2
        assert all(r.metadata["tier"] == "working" for r in filtered_results)
    
    @pytest.mark.asyncio
    async def test_complex_metadata_filtering(self, service):
        """Test complex filtering with operators."""
        results = [
            SearchResult.create(
                memory_id="mem1",
                content="High confidence result",
                confidence=0.9,
                metadata={"access_count": 10, "importance": 0.8}
            ),
            SearchResult.create(
                memory_id="mem2",
                content="Medium result",
                confidence=0.7,
                metadata={"access_count": 5, "importance": 0.6}
            )
        ]
        
        # Filter for access_count >= 8
        filters = {"access_count": {"op": "gte", "value": 8}}
        filtered_results = await service._apply_metadata_filters(results, filters)
        
        assert len(filtered_results) == 1
        assert filtered_results[0].memory_id == "mem1"
    
    @pytest.mark.asyncio
    async def test_significance_scoring_application(self, service, sample_query):
        """Test significance scoring application."""
        # Mock memory with high relevance
        high_importance_memory = Memory(
            user_id="user123",
            content="Important memory",
            tier=MemoryTier.LONG_TERM,
            importance=ImportanceScore.very_high(),
            access_count=20
        )
        # Make it recent
        high_importance_memory.created_at = datetime.now(timezone.utc) - timedelta(hours=1)
        
        service.memory_repository.get_by_id.return_value = high_importance_memory
        
        # Create initial result
        initial_result = SearchResult.create(
            memory_id="high_mem",
            content="Important memory",
            confidence=0.75,
            reasons=["vector_similarity"]
        )
        
        results = [initial_result]
        scored_results = await service._apply_significance_scoring(results, "user123")
        
        assert len(scored_results) == 1
        scored_result = scored_results[0]
        
        # Should have higher confidence due to significance scoring
        assert scored_result.confidence >= initial_result.confidence
        assert "significance_scoring" in scored_result.reasons
        
        # Check significance metadata
        significance = scored_result.metadata["significance"]
        assert 0.0 <= significance["combined"] <= 1.0
        assert all(0.0 <= significance[k] <= 1.0 for k in significance)
    
    @pytest.mark.asyncio
    async def test_result_deduplication(self, service):
        """Test search result deduplication."""
        duplicate_results = [
            SearchResult.create("mem1", "Content", 0.8),
            SearchResult.create("mem1", "Content", 0.7),  # Duplicate ID
            SearchResult.create("mem2", "Other content", 0.6),
            SearchResult.create("mem1", "Content", 0.9),  # Another duplicate
        ]
        
        unique_results = service._deduplicate_results(duplicate_results)
        
        # Should keep only one result per ID (the last one is kept with confidence 0.9)
        assert len(unique_results) == 2
        memory_ids = [r.memory_id for r in unique_results]
        assert "mem1" in memory_ids and "mem2" in memory_ids
    
    @pytest.mark.asyncio
    async def test_context_assembly(self, service, sample_query):
        """Test context assembly with token limits."""
        # Create results with varying content lengths
        results = [
            SearchResult.create("mem1", "Short content", 0.8),
            SearchResult.create("mem2", "A" * 4000, 0.7),  # ~4000 chars (~1000 tokens)
            SearchResult.create("mem3", "B" * 4000, 0.6),  # Another 1000 tokens
            SearchResult.create("mem4", "Medium length content", 0.5)
        ]
        
        # Mock the get_by_id method for context assembly
        service.memory_repository.get_by_id.return_value = Memory(
            user_id="user123",
            content="Test memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium()
        )
        
        context_results = await service._assemble_context(results, sample_query)
        
        # Should include shorter results until token limit is hit
        assert len(context_results) >= 2  # Short content + first long content
        # Should not exceed reasonable limit for demonstration
        assert len(context_results) < len(results)


class TestIntentClassifier:
    """Test cases for IntentClassifier."""
    
    @pytest.fixture
    def classifier(self):
        """Create intent classifier."""
        return IntentClassifier()
    
    @pytest.mark.asyncio
    async def test_intent_classification(self, classifier):
        """Test intent classification."""
        intent = await classifier.classify_intent("What is Python programming?")
        
        assert intent == SearchIntent.FACTUAL
        
        # Should be cached
        cached_intent = classifier.get_cached_intent("What is Python programming?")
        assert cached_intent == SearchIntent.FACTUAL
        assert cached_intent is intent  # Same cached object
    
    @pytest.mark.asyncio
    async def test_pattern_intent_classification(self, classifier):
        """Test pattern intent classification."""
        intent = await classifier.classify_intent("What patterns do I usually follow?")
        
        assert intent == SearchIntent.PATTERN
    
    @pytest.mark.asyncio
    async def test_intent_caching(self, classifier):
        """Test intent result caching."""
        query = "Tell me about machine learning"
        
        # First call should compute and cache
        intent1 = await classifier.classify_intent(query)
        assert intent1 == SearchIntent.FACTUAL
        
        # Second call should return cached result
        intent2 = classifier.get_cached_intent(query.lower())
        assert intent2 == SearchIntent.FACTUAL
        assert intent2 is intent1
    
    def test_cache_miss(self, classifier):
        """Test cache miss for unknown query."""
        cached_intent = classifier.get_cached_intent("unknown query")
        assert cached_intent is None


class TestSignificanceScorer:
    """Test cases for SignificanceScorer."""
    
    @pytest.fixture
    def scorer(self):
        """Create significance scorer."""
        return SignificanceScorer()
    
    @pytest.mark.asyncio
    async def test_significance_calculation(self, scorer):
        """Test significance score calculation."""
        memory = Memory(
            user_id="user123",
            content="Important memory",
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.high(),
            access_count=15
        )
        # Make memory moderately recent
        memory.created_at = datetime.now(timezone.utc) - timedelta(hours=12)
        
        significance = await scorer.calculate_significance(memory, 0.8)
        
        # Verify Score has all components
        assert 0.0 <= significance.relevance <= 1.0
        assert 0.0 <= significance.repetition <= 1.0
        assert 0.0 <= significance.recency <= 1.0
        assert 0.0 <= significance.importance <= 1.0
        assert 0.0 <= significance.combined <= 1.0
    
    @pytest.mark.asyncio
    async def test_significance_with_user_context(self, scorer):
        """Test significance calculation with user context."""
        memory = Memory(
            user_id="user123",
            content="User memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium(),
            access_count=5
        )
        
        user_context = {
            "recent_searches": ["Python", "machine learning"],
            "preferred_tiers": ["working", "short_term"]
        }

        significance = await scorer.calculate_significance(
            memory, 0.7, user_context
        )
        
        # The basic calculation should still work
        assert significance.relevance == 0.7
        assert 0.0 <= significance.combined <= 1.0
    
    @pytest.mark.asyncio
    async def test_significance_caching(self, scorer):
        """Test significance score caching."""
        memory = Memory(
            user_id="user123",
            content="Test memory",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.medium()
        )
        
        # Calculate and cache score
        score1 = await scorer.calculate_significance(memory, 0.8)
        assert score1 is not None
        
        # Get cached score
        score2 = scorer.get_cached_score(memory.id)
        assert score2 == score1
