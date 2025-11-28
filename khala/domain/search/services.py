"""Domain services for search functionality.

These services contain business logic for search operations,
result processing, and optimization following DDD principles.
"""

import asyncio
from typing import List, Dict, Any, Optional, Tuple, Callable
from datetime import datetime, timezone
import numpy as np
import logging

from .entities import SearchSession, SearchMetric, SearchPattern, SearchIndex
from .value_objects import Query, SearchResult, SearchIntent, SignificanceScore, SearchPipeline, SearchModality
from ..memory.entities import Memory, Entity
from ..memory.value_objects import EmbeddingVector, ImportanceScore, MemoryTier

logger = logging.getLogger(__name__)


class HybridSearchService:
    """Domain service for hybrid search operations."""
    
    def __init__(self, memory_repository: Any, entity_repository: Any, query_expander: Optional['QueryExpander'] = None):
        """Initialize hybrid search service.
        
        Args:
            memory_repository: Repository for memory operations
            entity_repository: Repository for entity operations
            query_expander: Service for query expansion
        """
        self.memory_repository = memory_repository
        self.entity_repository = entity_repository
        self.query_expander = query_expander or QueryExpander()
    
    async def search(
        self, 
        query: Query, 
        pipeline: Optional[SearchPipeline] = None
    ) -> SearchSession:
        """Execute hybrid search with the specified pipeline."""
        if pipeline is None:
            pipeline = SearchPipeline.create_for_intent(query.intent)
        
        # Create search session
        session = SearchSession(user_id=query.user_id, query=query)
        
        start_time = datetime.now(timezone.utc)
        
        # Expand query if needed (Multi-Perspective Questions)
        expanded_queries = [query]
        if pipeline.should_execute_stage("query_expansion"):
            variations = await self.query_expander.expand_query(query)
            expanded_queries.extend(variations)
            logger.debug(f"Expanded query into {len(expanded_queries)} variations")

        # Execute search pipeline for all variations
        all_results = []
        for q in expanded_queries:
            results = await self._execute_search_pipeline(q, pipeline)
            all_results.extend(results)
        
        # Deduplicate results from variations
        results = self._deduplicate_results(all_results)
        
        # Calculate significance scores and rank
        if pipeline.should_execute_stage("significance"):
            results = await self._apply_significance_scoring(results, query.user_id)
        
        # Assemble context if requested
        if pipeline.should_execute_stage("context"):
            results = await self._assemble_context(results, query, limit=pipeline.final_top_k)
        
        end_time = datetime.now(timezone.utc)
        search_time_ms = (end_time - start_time).total_seconds() * 1000
        
        # Update session
        for result in results[:pipeline.final_top_k]:
            session.add_result(result)
        
        session.mark_completed(search_time_ms, len(results))
        
        return session
    
    async def _execute_search_pipeline(
        self, 
        query: Query, 
        pipeline: SearchPipeline
    ) -> List[SearchResult]:
        """Execute the main search pipeline stages."""
        candidate_results = []
        
        # Stage 1: Vector search
        if pipeline.should_execute_stage("vector"):
            vector_results = await self._vector_search(
                query, pipeline.vector_top_k,
                similarity_threshold=pipeline.vector_similarity_threshold
            )
            candidate_results.extend(vector_results)
            logger.debug(f"Vector search found {len(vector_results)} candidates")
        
        # Stage 2: BM25 search  
        if pipeline.should_execute_stage("bm25"):
            bm25_results = await self._bm25_search(query, pipeline.bm25_top_k)
            candidate_results.extend(bm25_results)
            logger.debug(f"BM25 search found {len(bm25_results)} candidates")
        
        # Stage 3: Metadata filtering
        if pipeline.should_execute_stage("metadata"):
            candidate_results = await self._apply_metadata_filters(
                candidate_results, query.filters
            )
        
        # Stage 4: Graph traversal (for pattern searches)
        if pipeline.should_execute_stage("graph"):
            graph_results = await self._graph_traversal_search(query)
            candidate_results.extend(graph_results)
        
        # Deduplicate and sort by confidence
        unique_results = self._deduplicate_results(candidate_results)
        return sorted(unique_results, key=lambda r: r.confidence, reverse=True)
    
    async def _vector_search(
        self, 
        query: Query, 
        top_k: int,
        similarity_threshold: float = 0.6
    ) -> List[SearchResult]:
        """Execute vector similarity search."""
        if not query.embedding:
            return []
        
        # Convert numpy array to list for database
        embedding_vector = EmbeddingVector(query.embedding.tolist())
        
        # Search using repository with filters
        memory_records = await self.memory_repository.search_by_vector(
            embedding_vector, 
            query.user_id,
            top_k,
            min_similarity=similarity_threshold,
            filters=query.filters
        )
        
        results = []
        for record in memory_records:
            memory_id = record.get("id")
            if not memory_id:
                continue

            # Calculate confidence from similarity score
            confidence = record.get("similarity", 0.0)
            
            result = SearchResult.create(
                memory_id=memory_id,
                content=record.get("content", ""),
                confidence=confidence,
                reasons=["vector_similarity"],
                metadata={
                    "tier": record.get("tier"),
                    "access_count": record.get("access_count", 0),
                    "search_type": "vector"
                }
            )
            results.append(result)
        
        return results
    
    async def _bm25_search(self, query: Query, top_k: int) -> List[SearchResult]:
        """Execute BM25 full-text search."""
        memory_records = await self.memory_repository.search_by_text(
            query.text,
            query.user_id,
            top_k,
            filters=query.filters
        )
        
        results = []
        for record in memory_records:
            memory_id = record.get("id")
            if not memory_id:
                continue

            # Calculate confidence from relevance score
            confidence = min(1.0, record.get("relevance", 0.0))
            
            result = SearchResult.create(
                memory_id=memory_id,
                content=record.get("content", ""),
                confidence=confidence,
                reasons=["text_relevance"],
                metadata={
                    "tier": record.get("tier"),
                    "access_count": record.get("access_count", 0),
                    "search_type": "bm25"
                }
            )
            results.append(result)
        
        return results
    
    async def _apply_metadata_filters(
        self, 
        results: List[SearchResult], 
        filters: Dict[str, Any]
    ) -> List[SearchResult]:
        """Apply metadata filters to search results."""
        if not filters:
            return results
        
        filtered_results = []
        
        for result in results:
            result_metadata = result.metadata
            
            # Apply each filter
            passes_all_filters = True
            
            for filter_key, filter_value in filters.items():
                if not self._passes_metadata_filter(
                    result_metadata, filter_key, filter_value
                ):
                    passes_all_filters = False
                    break
            
            if passes_all_filters:
                filtered_results.append(result)
        
        return filtered_results
    
    def _passes_metadata_filter(
        self, 
        metadata: Dict[str, Any], 
        filter_key: str, 
        filter_value: Any
    ) -> bool:
        """Check if metadata passes a specific filter."""
        value = metadata.get(filter_key)
        
        if value is None:
            return False
        
        # Handle different filter types
        if isinstance(filter_value, (list, tuple)):
            # Filter by inclusion in list
            return value in filter_value
        elif isinstance(filter_value, dict):
            # Complex filter with operators
            op = filter_value.get("op", "eq")
            target = filter_value.get("value")

            if op == "eq":
                return value == target

            if target is None:
                return False
            elif op == "gt":
                return value > target
            elif op == "lt":
                return value < target
            elif op == "gte":
                return value >= target
            elif op == "lte":
                return value <= target
            elif op == "contains":
                return target in str(value)
        else:
            # Simple equality
            return value == filter_value
        
        return False
    
    async def _graph_traversal_search(self, query: Query) -> List[SearchResult]:
        """Execute graph traversal search for entity relationships."""
        # This would implement multi-hop entity search
        # For now, return empty placeholder
        return []
    
    async def _apply_significance_scoring(
        self, 
        results: List[SearchResult], 
        user_id: str
    ) -> List[SearchResult]:
        """Apply significance scoring to improve result ranking."""
        scored_results = []
        
        for result in results:
            # Get memory details for scoring
            memory = await self.memory_repository.get_by_id(result.memory_id)
            if not memory:
                continue
            
            # Calculate significance score
            age_hours = memory.get_age_hours()
            significance = SignificanceScore.calculate(
                similarity=result.confidence,
                access_count=memory.access_count,
                age_hours=age_hours,
                importance=memory.importance.value
            )
            
            # Update result with new confidence (significance score)
            updated_result = SearchResult.create(
                memory_id=result.memory_id,
                content=result.content,
                confidence=significance.combined,
                reasons=result.reasons + ["significance_scoring"],
                metadata={
                    **result.metadata,
                    "significance": {
                        "relevance": significance.relevance,
                        "repetition": significance.repetition,
                        "recency": significance.recency,
                        "importance": significance.importance,
                        "combined": significance.combined
                    }
                }
            )
            scored_results.append(updated_result)
        
        return scored_results
    
    async def _assemble_context(
        self, 
        results: List[SearchResult], 
        query: Query
    ) -> List[SearchResult]:
        """Assemble context for the results (token management)."""
        # Implement token counting and dynamic window sizing
        # This would be more complex in production
        
        max_tokens = 8000  # Example limit for Gemini
        total_tokens = 0
        
        context_results = []
        
        for result in results:
            # Simple token estimation (4 chars per token approximation)
            content_tokens = len(result.content) // 4
            
            if total_tokens + content_tokens <= max_tokens:
                context_results.append(result)
                total_tokens += content_tokens
            else:
                break
        
        return context_results
    
    def _deduplicate_results(self, results: List[SearchResult]) -> List[SearchResult]:
        """Remove duplicate search results."""
        seen_ids = set()
        unique_results = []
        
        for result in results:
            if result.memory_id not in seen_ids:
                seen_ids.add(result.memory_id)
                unique_results.append(result)
        
        return unique_results


class IntentClassifier:
    """Domain service for query intent classification."""
    
    def __init__(self):
        """Initialize intent classifier."""
        # In production, this would use a trained model
        self._intent_cache: Dict[str, SearchIntent] = {}
    
    async def classify_intent(self, query_text: str) -> SearchIntent:
        """Classify the intent of a query."""
        # Simple rule-based classification (would use Gemini in production)
        intent = SearchIntent.classify_text(query_text)
        
        # Cache the result
        self._intent_cache[query_text.lower()] = intent
        
        return intent
    
    def get_cached_intent(self, query_text: str) -> Optional[SearchIntent]:
        """Get cached intent classification."""
        return self._intent_cache.get(query_text.lower())


class SignificanceScorer:
    """Domain service for search result significance scoring."""
    
    def __init__(self):
        """Initialize significance scorer."""
        self._scoring_cache: Dict[str, SignificanceScore] = {}
    
    async def calculate_significance(
        self,
        memory: Memory,
        similarity: float
    ) -> SignificanceScore:
        """Calculate significance score for a memory."""
        age_hours = memory.get_age_hours()
        
        significance = SignificanceScore.calculate(
            similarity=similarity,
            access_count=memory.access_count,
            age_hours=age_hours,
            importance=memory.importance.value
        )
        
        return significance
    
    def get_cached_score(self, memory_id: str) -> Optional[SignificanceScore]:
        """Get cached significance score."""
        return self._scoring_cache.get(memory_id)


class QueryExpander:
    """Domain service for generating multi-perspective query variations."""
    
    async def expand_query(self, query: Query) -> List[Query]:
        """Generate variations of the original query."""
        # In a real implementation, this would call an LLM
        # For now, we use simple rule-based expansion
        
        variations = []
        text = query.text.lower()
        
        # 1. Synonym expansion (mock)
        if "how to" in text:
            variations.append(query.with_filters(type="guide"))
        
        # 2. Aspect expansion
        if query.intent == SearchIntent.LEARNING:
            variations.append(Query(
                text=f"examples of {query.text}",
                intent=query.intent,
                embedding=query.embedding,
                user_id=query.user_id,
                filters=query.filters,
                limit=query.limit,
                modality=query.modality
            ))
            variations.append(Query(
                text=f"concepts related to {query.text}",
                intent=query.intent,
                embedding=query.embedding,
                user_id=query.user_id,
                filters=query.filters,
                limit=query.limit,
                modality=query.modality
            ))
            
        return variations


class SessionAnalyzer:
    """Domain service for analyzing cross-session patterns."""
    
    def __init__(self, client: Any):
        self.client = client
        
    async def analyze_cross_session_patterns(self, user_id: str) -> List[SearchPattern]:
        """Analyze past sessions to find recurring patterns."""
        sessions = await self.client.get_user_sessions(user_id, limit=50)
        
        patterns = []
        
        # 1. Topic Frequency Analysis
        topic_counts = {}
        for session in sessions:
            # Assuming session has 'query' field which is a dict or object
            query_data = session.get('query', {})
            # Handle both dict and object (if deserialized)
            if isinstance(query_data, dict):
                query_text = query_data.get('text', '')
            else:
                query_text = getattr(query_data, 'text', '')
                
            # Simple keyword extraction (mock)
            words = [w for w in query_text.split() if len(w) > 4]
            for w in words:
                topic_counts[w] = topic_counts.get(w, 0) + 1
                
        for topic, count in topic_counts.items():
            if count >= 3:
                patterns.append(SearchPattern(
                    pattern_type="topic_cluster",
                    user_id=user_id,
                    pattern_data={"topic": topic, "count": count},
                    frequency=count,
                    confidence=min(1.0, count / 10.0),
                    last_seen=datetime.now(timezone.utc)
                ))
                
        return patterns
