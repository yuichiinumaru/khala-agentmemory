from typing import List, Dict, Any, Optional
import logging
from khala.domain.memory.repository import MemoryRepository
from khala.domain.ports.embedding_service import EmbeddingService
from khala.domain.memory.entities import Memory, EmbeddingVector

logger = logging.getLogger(__name__)

class HybridSearchService:
    """
    Service for performing hybrid search (Vector + BM25) with Reciprocal Rank Fusion.
    """
    def __init__(
        self,
        memory_repository: MemoryRepository,
        embedding_service: EmbeddingService
    ):
        self.memory_repo = memory_repository
        self.embedding_service = embedding_service

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
        vector_weight: float = 1.0,
        bm25_weight: float = 1.0
    ) -> List[Memory]:
        """
        Perform hybrid search using Reciprocal Rank Fusion (RRF).

        Args:
            query: The search query string.
            user_id: The ID of the user performing the search.
            top_k: Number of final results to return.
            filters: Optional metadata filters.
            rrf_k: Constant for RRF formula (default 60).
            vector_weight: Weight for vector search results (default 1.0).
            bm25_weight: Weight for BM25 search results (default 1.0).

        Returns:
            List of unique Memory objects sorted by RRF score.
        """
        # 1. Fetch candidates in parallel (conceptually, here async)
        # We fetch top_k * 2 candidates from each source to ensure good fusion overlap
        candidate_k = top_k * 2

        # 1a. Vector Search
        vector_results: List[Memory] = []
        try:
            embedding_values = await self.embedding_service.get_embedding(query)
            embedding = EmbeddingVector(values=embedding_values)
            vector_results = await self.memory_repo.search_by_vector(
                embedding=embedding,
                user_id=user_id,
                top_k=candidate_k,
                filters=filters
            )
        except Exception as e:
            logger.error(f"Vector search failed: {e}")
            # Continue with just BM25 if vector fails

        # 1b. BM25 Search
        bm25_results: List[Memory] = []
        try:
            bm25_results = await self.memory_repo.search_by_text(
                query_text=query,
                user_id=user_id,
                top_k=candidate_k,
                filters=filters
            )
        except Exception as e:
            logger.error(f"BM25 search failed: {e}")
            # Continue with just Vector if BM25 fails

        if not vector_results and not bm25_results:
            return []

        # 2. Compute RRF Scores
        # Map memory_id -> score
        scores: Dict[str, float] = {}
        # Map memory_id -> Memory object
        memories: Dict[str, Memory] = {}

        # Process Vector Results
        for rank, memory in enumerate(vector_results):
            memories[memory.id] = memory
            scores[memory.id] = scores.get(memory.id, 0.0) + \
                (vector_weight * (1.0 / (rrf_k + rank + 1)))

        # Process BM25 Results
        for rank, memory in enumerate(bm25_results):
            memories[memory.id] = memory
            scores[memory.id] = scores.get(memory.id, 0.0) + \
                (bm25_weight * (1.0 / (rrf_k + rank + 1)))

        # 3. Sort by Score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # 4. Return top_k results
        final_results = [memories[mid] for mid in sorted_ids[:top_k]]

        return final_results
