"""Unit tests for search domain value objects.

Following TDD principles, these tests verify the business logic
and constraints of search-related value objects.
"""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta

from khala.domain.search.value_objects import (
    SearchIntent,
    SearchResult,
    SignificanceScore,
    Query,
    SearchPipeline
)
from khala.domain.memory.value_objects import EmbeddingVector


class TestSearchIntent:
    """Test cases for SearchIntent value object."""
    
    def test_intent_classification_factual(self):
        """Test factual intent classification."""
        queries = [
            "What is Python?",
            "Who is the president?",
            "When was JavaScript created?",
            "Where is Paris located?",
            "Tell me about machine learning"
        ]
        
        for query in queries:
            intent = SearchIntent.classify_text(query)
            print(f"Query: '{query}' -> Intent: {intent}")
            assert intent == SearchIntent.FACTUAL
            assert intent.get_search_method() == "standard"
    
    def test_intent_classification_pattern(self):
        """Test pattern intent classification."""
        queries = [
            "What patterns do I use?",
            "How often do I do this?",
            "My usual workflow",
            "Typical behavior patterns",
            "Trends in my code"
        ]
        
        for query in queries:
            intent = SearchIntent.classify_text(query)
            assert intent == SearchIntent.PATTERN
            assert intent.get_search_method() == "graph"
    
    def test_intent_classification_decision(self):
        """Test decision intent classification."""
        queries = [
            "Should I use Python or JavaScript?",
            "What should I do next?",
            "Help me decide between options",
            "Which is better?"
        ]
        
        for query in queries:
            intent = SearchIntent.classify_text(query)
            assert intent == SearchIntent.DECISION
            assert intent.get_search_method() == "importance_filtered"
    
    def test_intent_classification_default(self):
        """Test default (standard) intent classification."""
        queries = [
            "random query",
            "something not recognized",
            "unclear intent"
        ]
        
        for query in queries:
            intent = SearchIntent.classify_text(query)
            assert intent == SearchIntent.STANDARD
            assert intent.get_search_method() == "standard"
    
    def test_all_intents_have_search_methods(self):
        """Test that all intents have defined search methods."""
        for intent in SearchIntent:
            method = intent.get_search_method()
            assert isinstance(method, str)
            assert method in ["standard", "graph", "importance_filtered", "hybrid"]


class TestSearchResult:
    """Test cases for SearchResult value object."""
    
    def test_valid_search_result_creation(self):
        """Test creating a valid search result."""
        result = SearchResult.create(
            memory_id="mem123",
            content="Test content",
            confidence=0.85,
            reasons=["vector_similarity"],
            metadata={"tier": "working"}
        )
        
        assert result.memory_id == "mem123"
        assert result.content == "Test content"
        assert result.confidence == 0.85
        assert result.reasons == ["vector_similarity"]
        assert result.metadata["tier"] == "working"
    
    def test_search_result_empty_memory_id(self):
        """Test search result with empty memory ID."""
        with pytest.raises(ValueError, match="Memory ID cannot be empty"):
            SearchResult.create(
                memory_id="",
                content="Test content",
                confidence=0.85
            )
    
    def test_search_result_empty_content(self):
        """Test search result with empty content."""
        with pytest.raises(ValueError, match="Content cannot be empty"):
            SearchResult.create(
                memory_id="mem123",
                content="",
                confidence=0.85
            )
    
    def test_search_result_invalid_confidence(self):
        """Test search result with invalid confidence."""
        # Too high
        with pytest.raises(ValueError, match="Confidence must be in"):
            SearchResult.create(
                memory_id="mem123",
                content="Test content",
                confidence=1.5
            )
        
        # Too low
        with pytest.raises(ValueError, match="Confidence must be in"):
            SearchResult.create(
                memory_id="mem123",
                content="Test content",
                confidence=-0.1
            )
    
    def test_search_result_with_defaults(self):
        """Test search result creation with defaults."""
        result = SearchResult.create(
            memory_id="mem123",
            content="Test content",
            confidence=0.75
        )
        
        assert result.reasons == []
        assert result.metadata == {}


class TestSignificanceScore:
    """Test cases for SignificanceScore value object."""
    
    def test_significance_score_calculation(self):
        """Test calculating significance score."""
        significance = SignificanceScore.calculate(
            similarity=0.8,
            access_count=10,
            age_hours=24,  # 1 day old
            importance=0.7
        )
        
        # Check that all components are in valid range
        assert 0.0 <= significance.relevance <= 1.0
        assert 0.0 <= significance.repetition <= 1.0
        assert 0.0 <= significance.recency <= 1.0
        assert 0.0 <= significance.importance <= 1.0
        assert 0.0 <= significance.combined <= 1.0
    
    def test_significance_score_high_similarity(self):
        """Test significance score with high similarity."""
        significance = SignificanceScore.calculate(
            similarity=0.95,
            access_count=1,
            age_hours=1,  # Very recent
            importance=0.9
        )
        
        # High similarity and importance should give high combined score
        assert significance.combined > 0.7
    
    def test_significance_score_old_low_access(self):
        """Test significance score for old, rarely accessed memory."""
        significance = SignificanceScore.calculate(
            similarity=0.6,
            access_count=1,
            age_hours=720,  # 30 days old
            importance=0.3
        )
        
        # Low across all metrics should give low combined score
        assert significance.combined < 0.5
    
    def test_significance_score_custom_weights(self):
        """Test significance score with custom weights."""
        significance = SignificanceScore.calculate(
            similarity=0.8,
            access_count=5,
            age_hours=12,
            importance=0.7,
            relevance_weight=0.6,  # Emphasize relevance
            repetition_weight=0.1,
            recency_weight=0.1,  
            importance_weight=0.2
        )
        
        # With higher relevance weight, relevance should dominate
        assert significance.relevance == 0.8
        assert significance.combined > 0.7  # Should be higher due to weight
    
    def test_significance_score_invalid_components(self):
        """Test significance score with invalid component values."""
        # Invalid similarity
        with pytest.raises(ValueError, match="relevance must be in"):
            SignificanceScore.calculate(
                similarity=1.5,  # Too high
                access_count=1,
                age_hours=1,
                importance=0.5
            )
        
        # Invalid importance
        with pytest.raises(ValueError, match="importance must be in"):
            SignificanceScore.calculate(
                similarity=0.8,
                access_count=1,
                age_hours=1,
                importance=-0.1  # Too low
            )


class TestQuery:
    """Test cases for Query value object."""
    
    def test_valid_query_creation(self):
        """Test creating a valid query."""
        embedding = np.array([0.1] * 768)
        query = Query(
            text="Python programming",
            intent=SearchIntent.FACTUAL,
            embedding=embedding,
            user_id="user123"
        )
        
        assert query.text == "Python programming"
        assert query.intent == SearchIntent.FACTUAL
        assert query.user_id == "user123"
        assert query.limit == 10  # Default limit
        assert query.filters == {}  # Default empty filters
    
    def test_query_with_parameters(self):
        """Test query creation with all parameters."""
        embedding = np.array([0.1] * 768)
        filters = {"tier": "working", "min_importance": 0.7}
        
        query = Query(
            text="Search query",
            intent=SearchIntent.PATTERN,
            embedding=embedding,
            user_id="user123",
            filters=filters,
            limit=20
        )
        
        assert query.filters == filters
        assert query.limit == 20
    
    def test_query_empty_text(self):
        """Test query with empty text."""
        with pytest.raises(ValueError, match="Query text cannot be empty"):
            Query(
                text="",
                intent=SearchIntent.FACTUAL,
                embedding=None,
                user_id="user123"
            )
    
    def test_query_empty_user_id(self):
        """Test query with empty user ID."""
        with pytest.raises(ValueError, match="User ID cannot be empty"):
            Query(
                text="Test query",
                intent=SearchIntent.FACTUAL,
                embedding=None,
                user_id=""
            )
    
    def test_query_negative_limit(self):
        """Test query with negative limit."""
        embedding = np.array([0.1] * 768)
        with pytest.raises(ValueError, match="Limit must be positive"):
            Query(
                text="Test query",
                intent=SearchIntent.FACTUAL,
                embedding=embedding,
                user_id="user123",
                limit=-5
            )
    
    def test_query_with_filters(self):
        """Test creating query with filters."""
        query = Query(
            text="Test query",
            intent=SearchIntent.FACTUAL,
            embedding=None,
            user_id="user123"
        )
        
        # Add filters using with_filters method
        filtered_query = query.with_filters(tier="working", min_importance=0.7)
        
        expected_filters = {"tier": "working", "min_importance": 0.7}
        assert filtered_query.filters == expected_filters
        
        # Original query should be unchanged (immutable)
        assert query.filters == {}
    
    def test_query_with_limit(self):
        """Test creating query with different limit."""
        query = Query(
            text="Test query",
            intent=SearchIntent.FACTUAL,
            embedding=None,
            user_id="user123"
        )
        
        limited_query = query.with_limit(25)
        assert limited_query.limit == 25
        
        # Original query should be unchanged
        assert query.limit == 10
    
    def test_query_limit_clamping(self):
        """Test query limit clamping to minimum value."""
        query = Query(
            text="Test query",
            intent=SearchIntent.FACTUAL,
            embedding=None,
            user_id="user123"
        )
        
        limited_query = query.with_limit(0)  # Should clamp to 1
        assert limited_query.limit == 1


class TestSearchPipeline:
    """Test cases for SearchPipeline value object."""
    
    def test_default_pipeline(self):
        """Test default search pipeline configuration."""
        pipeline = SearchPipeline()
        
        assert pipeline.vector_enabled is True
        assert pipeline.bm25_enabled is True
        assert pipeline.metadata_filtering is True
        assert pipeline.graph_traversal is False
        assert pipeline.significance_scoring is True
        assert pipeline.context_assembly is True
    
    def test_pipeline_for_pattern_intent(self):
        """Test pipeline optimized for pattern search."""
        pipeline = SearchPipeline.create_for_intent(SearchIntent.PATTERN)
        
        assert pipeline.vector_enabled is True
        assert pipeline.bm25_enabled is True
        assert pipeline.graph_traversal is True  # Enabled for patterns
        assert pipeline.final_top_k == 20  # More results for patterns
        assert pipeline.vector_top_k == 200
        assert pipeline.bm25_top_k == 100
    
    def test_pipeline_for_decision_intent(self):
        """Test pipeline optimized for decision search."""
        pipeline = SearchPipeline.create_for_intent(SearchIntent.DECISION)
        
        assert pipeline.min_confidence == 0.5  # Higher threshold for decisions
        assert pipeline.final_top_k == 5  # Fewer, higher quality results
    
    def test_pipeline_stage_execution(self):
        """Test pipeline stage execution checks."""
        pipeline = SearchPipeline(
            vector_enabled=True,
            bm25_enabled=False,
            graph_traversal=True
        )
        
        assert pipeline.should_execute_stage("vector") is True
        assert pipeline.should_execute_stage("bm25") is False
        assert pipeline.should_execute_stage("graph") is True
        assert pipeline.should_execute_stage("metadata") is True
        assert pipeline.should_execute_stage("significance") is True
        assert pipeline.should_execute_stage("context") is True
    
    def test_pipeline_all_stages_enabled(self):
        """Test pipeline with all stages enabled."""
        pipeline = SearchPipeline(
            vector_enabled=True,
            bm25_enabled=True,
            metadata_filtering=True,
            graph_traversal=True,
            significance_scoring=True,
            context_assembly=True
        )
        
        for stage in ["vector", "bm25", "metadata", "graph", "significance", "context"]:
            assert pipeline.should_execute_stage(stage)
    
    def test_pipeline_all_stages_disabled(self):
        """Test pipeline with all stages disabled."""
        pipeline = SearchPipeline(
            vector_enabled=False,
            bm25_enabled=False,
            metadata_filtering=False,
            graph_traversal=False,
            significance_scoring=False,
            context_assembly=False
        )
        
        for stage in ["vector", "bm25", "metadata", "graph", "significance", "context"]:
            assert not pipeline.should_execute_stage(stage)
