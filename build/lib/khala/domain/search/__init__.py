"""Search domain for KHALA.

This module contains the core search domain logic including
hybrid search, intent classification, and significance scoring.
"""

from .value_objects import SearchIntent, SearchResult, SignificanceScore, Query, SearchPipeline
from .services import HybridSearchService, IntentClassifier, SignificanceScorer
from .entities import SearchSession, SearchMetric, SearchPattern, SearchIndex, SearchOptimization

__all__ = [
    "SearchIntent",
    "SearchResult", 
    "SignificanceScore",
    "Query",
    "SearchPipeline",
    "HybridSearchService",
    "IntentClassifier",
    "SignificanceScorer",
    "SearchSession",
    "SearchMetric",
    "SearchPattern",
    "SearchIndex",
    "SearchOptimization",
]
