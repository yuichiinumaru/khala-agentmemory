"""KHALA - Knowledge Hierarchical Adaptive Long-term Agent.

KHALA is a production-ready memory system for AI agents that implements
57 memory optimization strategies using Agno + SurrealDB.
"""

__version__ = "2.0.0"
__author__ = "KHALA Team"
__email__ = "khala@example.com"

# Export key classes without importing heavy dependencies
# These can be imported when needed
try:
    from khala.domain.memory.entities import Memory, MemoryTier
    _has_domain = True
except ImportError:
    _has_domain = False

__all__ = [
    "__version__",
]
