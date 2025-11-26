"""Domain entities for the search system.

These entities represent search-related business concepts and
contain search logic following DDD principles.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional, Tuple
import uuid

from .value_objects import Query, SearchResult, SearchIntent, SignificanceScore
from ..memory.value_objects import EmbeddingVector


@dataclass
class SearchSession:
    """Entity representing a search session with context."""
    
    user_id: str
    query: Query
    
    # Session tracking
    session_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    
    # Search results and metrics
    results: List[SearchResult] = field(default_factory=list)
    total_searched: int = 0
    search_time_ms: float = 0.0
    
    # Context tracking
    previous_queries: List[str] = field(default_factory=list)
    response_user_id: Optional[str] = None  # For multi-agent coordination
    topics: List[str] = field(default_factory=list) # Extracted topics for cross-session analysis
    
    def add_result(self, result: SearchResult) -> None:
        """Add a search result to the session."""
        self.results.append(result)
    
    def mark_completed(self, search_time_ms: float, total_searched: int) -> None:
        """Mark the search session as completed."""
        self.completed_at = datetime.now(timezone.utc)
        self.search_time_ms = search_time_ms
        self.total_searched = total_searched
    
    def get_top_results(self, n: int = 5) -> List[SearchResult]:
        """Get top N results sorted by confidence."""
        return sorted(self.results, key=lambda r: r.confidence, reverse=True)[:n]
    
    def get_average_confidence(self) -> float:
        """Calculate average confidence of results."""
        if not self.results:
            return 0.0
        return sum(r.confidence for r in self.results) / len(self.results)
    
    def is_completed(self) -> bool:
        """Check if the search session is completed."""
        return self.completed_at is not None
    
    def add_previous_query(self, query_text: str) -> None:
        """Add a previous query for context tracking."""
        if query_text not in self.previous_queries:
            self.previous_queries.append(query_text)
            # Keep only last 10 queries
            if len(self.previous_queries) > 10:
                self.previous_queries = self.previous_queries[-10:]


@dataclass
class SearchMetric:
    """Entity representing search performance metrics."""
    
    user_id: str
    session_id: str
    
    # Performance metrics
    search_time_ms: float
    memory_count_searched: int
    results_returned: int
    average_confidence: float
    
    # Query characteristics
    query_text: str
    intent: SearchIntent
    pipeline_stages: List[str] = field(default_factory=list)
    
    # Quality metrics
    precision_at_5: float = 0.0
    precision_at_10: float = 0.0
    recall: float = 0.0  # Approximate recall estimate
    user_feedback: Optional[int] = None  # 1-5 rating
    
    # Timestamps
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def calculate_precision(self, results: List[SearchResult]) -> None:
        """Calculate precision@k metrics."""
        if len(results) >= 5:
            self.precision_at_5 = sum(1 for r in results[:5] if r.confidence > 0.7) / min(5, len(results))
        
        if len(results) >= 10:
            self.precision_at_10 = sum(1 for r in results[:10] if r.confidence > 0.7) / min(10, len(results))
    
    def get_efficiency_score(self) -> float:
        """Calculate search efficiency score."""
        # Normalize metrics and combine
        time_score = max(0, (1000 - self.search_time_ms) / 1000)  # Faster is better
        coverage_score = min(1, self.results_returned / max(1, self.memory_count_searched))
        confidence_score = self.average_confidence
        
        # Weighted combination
        return (time_score * 0.3 + coverage_score * 0.3 + confidence_score * 0.4)


@dataclass
class SearchPattern:
    """Entity representing recurring search patterns."""
    
    pattern_type: str  # "query_frequency", "time_of_day", "topic_cluster"
    user_id: str
    pattern_data: Dict[str, Any] = field(default_factory=dict)
    
    # Pattern metrics
    frequency: int = 0  # How often this pattern occurs
    confidence: float = 0.0  # Pattern strength
    last_seen: Optional[datetime] = None
    
    # Metadata
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def update_frequency(self) -> None:
        """Update pattern frequency."""
        self.frequency += 1
        self.last_seen = datetime.now(timezone.utc)
    
    def calculate_confidence(self, total_occurrences: int) -> float:
        """Calculate pattern confidence based on frequency."""
        if total_occurrences == 0:
            return 0.0
        return min(1.0, self.frequency / total_occurrences)
    
    def is_recent(self, hours: int = 24) -> bool:
        """Check if pattern was seen recently."""
        if not self.last_seen:
            return False
        
        age_hours = (datetime.now(timezone.utc) - self.last_seen).total_seconds() / 3600
        return age_hours <= hours


@dataclass  
class SearchIndex:
    """Entity representing search index metadata."""
    
    index_name: str
    index_type: str  # "vector", "bm25", "metadata"
    
    # Index statistics
    total_items: int = 0
    index_size_mb: float = 0.0
    last_updated: Optional[datetime] = None
    
    # Performance metrics  
    query_count: int = 0
    avg_query_time_ms: float = 0.0
    cache_hit_rate: float = 0.0
    
    # Configuration
    is_enabled: bool = True
    priority: int = 1  # For routing decisions
    
    def update_statistics(
        self, 
        query_time_ms: float, 
        cache_hit: bool = False,
        items_added: int = 0
    ) -> None:
        """Update index statistics."""
        self.query_count += 1
        
        # Update average query time
        if self.query_count == 1:
            self.avg_query_time_ms = query_time_ms
        else:
            # Exponential moving average with alpha=0.1
            alpha = 0.1
            self.avg_query_time_ms = (
                alpha * query_time_ms + 
                (1 - alpha) * self.avg_query_time_ms
            )
        
        # Update cache hit rate
        total_queries = self.query_count
        self.cache_hit_rate = (
            (self.cache_hit_rate * (total_queries - 1) + (1.0 if cache_hit else 0.0))
            / total_queries
        )
        
        # Update item count and timestamp
        self.total_items += items_added
        if items_added > 0:
            self.last_updated = datetime.now(timezone.utc)
    
    def should_use(self, query_type: str) -> bool:
        """Determine if this index should be used for the query type."""
        if not self.is_enabled:
            return False
        
        priority_map = {
            "vector": ["vector"],
            "bm25": ["text", "keyword"],
            "metadata": ["filter", "exact"],
        }
        
        return self.index_type in priority_map.get(query_type, [])


@dataclass
class SearchOptimization:
    """Entity representing search optimization strategies."""
    
    optimization_type: str  # "caching", "query_rewrite", "result_rerank"
    user_id: str
    
    # Optimization configuration
    enabled: bool = True
    parameters: Dict[str, Any] = field(default_factory=dict)
    
    # Performance metrics
    applications: int = 0  # How many times applied
    success_rate: float = 0.0
    avg_improvement_ms: float = 0.0
    
    # Metadata
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_applied: Optional[datetime] = None
    
    def apply_optimization(self, improvement_ms: float, successful: bool) -> None:
        """Record optimization application."""
        self.applications += 1
        self.last_applied = datetime.now(timezone.utc)
        
        # Update success rate
        if self.applications == 1:
            self.success_rate = 1.0 if successful else 0.0
        else:
            alpha = 0.1  # Exponential moving average
            self.success_rate = (
                alpha * (1.0 if successful else 0.0) +
                (1 - alpha) * self.success_rate
            )
        
        # Update average improvement
        if successful:
            if self.applications == 1:
                self.avg_improvement_ms = improvement_ms
            else:
                alpha = 0.1
                self.avg_improvement_ms = (
                    alpha * improvement_ms +
                    (1 - alpha) * self.avg_improvement_ms
                )
    
    def is_effective(self, min_success_rate: float = 0.7, min_improvement: float = 10.0) -> bool:
        """Check if optimization is effectively improving performance."""
        return (self.enabled and 
                self.success_rate >= min_success_rate and
                self.avg_improvement_ms >= min_improvement)
