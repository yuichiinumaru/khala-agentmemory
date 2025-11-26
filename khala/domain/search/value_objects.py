"""Value objects for the search domain.

Immutable value objects that represent search-related concepts
in the KHALA memory system.
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional, Tuple
from enum import Enum
import numpy as np


class SearchModality(Enum):
    """Supported search modalities."""
    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    CODE = "code"
    MULTIMODAL = "multimodal"


class SearchIntent(Enum):
    """Types of search intents for query routing."""
    
    FACTUAL = "factual"
    PATTERN = "pattern"
    DECISION = "decision"
    LEARNING = "learning" 
    DEBUG = "debug"
    PLANNING = "planning"
    ANALYSIS = "analysis"
    SYNTHESIS = "synthesis"
    STANDARD = "standard"
    
    @classmethod
    def classify_text(cls, query_text: str) -> "SearchIntent":
        """Classify query intent based on text patterns."""
        query_lower = query_text.lower()
        
        # Pattern matching for intent classification (more specific patterns first)
        intent_patterns = [
            (cls.FACTUAL, ["what is", "who is", "when was", "when did", "where is", "tell me about"]),
            (cls.LEARNING, ["how to", "understand", "tutorial"]),  # More specific learning patterns
            (cls.PATTERN, ["what patterns", "trends", "habits", "usual", "typical", "how often"]),
            (cls.DECISION, ["should i", "what should", "decide", "choice", "better", "recommend"]),
            (cls.DEBUG, ["error", "problem", "issue", "bug", "broken", "wrong"]),
            (cls.PLANNING, ["plan", "schedule", "timeline", "steps", "roadmap"]),
            (cls.ANALYSIS, ["analyze", "examine", "review", "evaluate", "compare"]),
            (cls.SYNTHESIS, ["combine", "integrate", "synthesize", "merge", "unify"]),
        ]
        
        for intent, patterns in intent_patterns:
            if any(pattern in query_lower for pattern in patterns):
                return intent
        
        # Generic learning check (only if no other patterns matched)
        if "learn" in query_lower or "explain" in query_lower:
            return cls.LEARNING
        
        return cls.STANDARD
    
    def get_search_method(self) -> str:
        """Get the search method for this intent."""
        method_map = {
            SearchIntent.FACTUAL: "standard",
            SearchIntent.PATTERN: "graph",
            SearchIntent.DECISION: "importance_filtered",
            SearchIntent.LEARNING: "hybrid",
            SearchIntent.DEBUG: "hybrid",
            SearchIntent.PLANNING: "hybrid",
            SearchIntent.ANALYSIS: "hybrid",
            SearchIntent.SYNTHESIS: "hybrid",
            SearchIntent.STANDARD: "standard",
        }
        return method_map[self]


@dataclass(frozen=True)
class SearchResult:
    """Immutable search result with scoring."""
    
    memory_id: str
    content: str
    confidence: float
    reasons: List[str]
    metadata: Dict[str, Any]
    
    def __post_init__(self) -> None:
        """Validate SearchResult."""
        if not self.memory_id.strip():
            raise ValueError("Memory ID cannot be empty")
        
        if not self.content.strip():
            raise ValueError("Content cannot be empty")
        
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be in [0.0, 1.0]")
    
    @classmethod
    def create(
        cls,
        memory_id: str,
        content: str,
        confidence: float,
        reasons: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> "SearchResult":
        """Create a SearchResult with defaults."""
        return cls(
            memory_id=memory_id,
            content=content,
            confidence=confidence,
            reasons=reasons or [],
            metadata=metadata or {}
        )


@dataclass(frozen=True)
class SignificanceScore:
    """Immutable significance score for search result ranking."""
    
    relevance: float  # Semantic similarity
    repetition: float  # Frequency of occurrence
    recency: float     # Time-based weighting
    importance: float  # Memory importance factor
    combined: float    # Final weighted score
    
    def __post_init__(self) -> None:
        """Validate significance score components."""
        for name, value in [
            ("relevance", self.relevance),
            ("repetition", self.repetition),
            ("recency", self.recency),
            ("importance", self.importance),
            ("combined", self.combined)
        ]:
            if not (0.0 <= value <= 1.0):
                raise ValueError(f"{name} must be in [0.0, 1.0], got {value}")
    
    @classmethod
    def calculate(
        cls,
        similarity: float,
        access_count: int,
        age_hours: float,
        importance: float,
        # Weights for the calculation (can be tuned)
        relevance_weight: float = 0.4,
        repetition_weight: float = 0.2,
        recency_weight: float = 0.2,
        importance_weight: float = 0.2
    ) -> "SignificanceScore":
        """Calculate significance score from input factors."""
        
        # Normalize access count to 0-1 range (log scaling)
        import math
        normalized_repetition = min(math.log1p(access_count) / math.log1p(100), 1.0)
        
        # Calculate recency score (more recent = higher score)
        max_age_hours = 30 * 24  # 30 days
        recency = max(0, (max_age_hours - age_hours) / max_age_hours)
        
        # Combine scores with weights
        combined = (
            similarity * relevance_weight +
            normalized_repetition * repetition_weight +
            recency * recency_weight +
            importance * importance_weight
        )
        
        return cls(
            relevance=similarity,
            repetition=normalized_repetition,
            recency=recency,
            importance=importance,
            combined=min(combined, 1.0)
        )


@dataclass(frozen=True)
class Query:
    """Immutable search query with context."""
    
    text: str
    intent: SearchIntent
    embedding: Optional[np.ndarray]
    user_id: str
    filters: Dict[str, Any] = None
    limit: int = 10
    modality: SearchModality = SearchModality.TEXT
    
    def __post_init__(self) -> None:
        """Validate query."""
        if not self.text.strip():
            raise ValueError("Query text cannot be empty")
        
        if not self.user_id.strip():
            raise ValueError("User ID cannot be empty")
        
        if self.limit <= 0:
            raise ValueError("Limit must be positive")
        
        if self.filters is None:
            object.__setattr__(self, 'filters', {})
    
    def with_filters(self, **filters) -> "Query":
        """Create new query with additional filters."""
        new_filters = self.filters.copy()
        new_filters.update(filters)
        
        return Query(
            text=self.text,
            intent=self.intent,
            embedding=self.embedding,
            user_id=self.user_id,
            filters=new_filters,
            limit=self.limit,
            modality=self.modality
        )
    
    def with_limit(self, limit: int) -> "Query":
        """Create new query with different limit."""
        return Query(
            text=self.text,
            intent=self.intent,
            embedding=self.embedding,
            user_id=self.user_id,
            filters=self.filters.copy(),
            limit=max(1, limit),
            modality=self.modality
        )


@dataclass(frozen=True)
class SearchPipeline:
    """Immutable configuration for search pipeline stages."""
    
    vector_enabled: bool = True
    bm25_enabled: bool = True
    metadata_filtering: bool = True
    graph_traversal: bool = False
    significance_scoring: bool = True
    context_assembly: bool = True
    
    # Vector search parameters
    vector_similarity_threshold: float = 0.6
    vector_top_k: int = 100
    
    # BM25 parameters
    bm25_top_k: int = 50
    
    # Result combination parameters
    final_top_k: int = 10
    min_confidence: float = 0.3
    
    @classmethod
    def create_for_intent(cls, intent: SearchIntent) -> "SearchPipeline":
        """Create search pipeline optimized for specific intent."""
        if intent == SearchIntent.PATTERN:
            # Pattern search uses graph traversal
            return cls(
                vector_enabled=True,
                bm25_enabled=True,
                metadata_filtering=True,
                graph_traversal=True,
                vector_top_k=200,
                bm25_top_k=100,
                final_top_k=20
            )
        elif intent == SearchIntent.DECISION:
            # Decision search filters by importance
            return cls(
                vector_enabled=True,
                bm25_enabled=True,
                metadata_filtering=True,
                min_confidence=0.5,
                final_top_k=5
            )
        else:
            # Standard configuration for other intents
            return cls()
    
    def should_execute_stage(self, stage: str) -> bool:
        """Check if a specific stage should be executed."""
        stage_map = {
            "vector": self.vector_enabled,
            "bm25": self.bm25_enabled,
            "metadata": self.metadata_filtering,
            "graph": self.graph_traversal,
            "significance": self.significance_scoring,
            "context": self.context_assembly
        }
        return stage_map.get(stage, False)
