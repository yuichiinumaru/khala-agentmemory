from typing import List, Dict, Any, Optional
import logging
import asyncio
from khala.domain.memory.repository import MemoryRepository
from khala.domain.ports.embedding_service import EmbeddingService
from khala.domain.memory.entities import Memory, EmbeddingVector
from khala.application.services.query_expansion_service import QueryExpansionService
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class HybridSearchService:
    """
    Service for performing hybrid search (Vector + BM25) with Reciprocal Rank Fusion.
    """
    def __init__(
        self,
        memory_repository: MemoryRepository,
        embedding_service: EmbeddingService,
        query_expansion_service: Optional[QueryExpansionService] = None,
        db_client: Optional[SurrealDBClient] = None
    ):
        self.memory_repo = memory_repository
        self.embedding_service = embedding_service
        self.query_expansion_service = query_expansion_service
        self.db_client = db_client

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
        vector_weight: float = 1.0,
        bm25_weight: float = 1.0,
        expand_query: bool = False
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
        # 0. Query Expansion
        expanded_queries = [query]
        if expand_query and self.query_expansion_service:
            expanded_queries = await self.query_expansion_service.expand_query(query)

        # 1. Fetch candidates in parallel for all queries
        # We fetch top_k * 2 candidates from each source to ensure good fusion overlap
        candidate_k = top_k * 2

        all_vector_results: List[Memory] = []
        all_bm25_results: List[Memory] = []

        for q in expanded_queries:
            # 1a. Vector Search
            try:
                embedding_values = await self.embedding_service.get_embedding(q)
                embedding = EmbeddingVector(values=embedding_values)
                v_results = await self.memory_repo.search_by_vector(
                    embedding=embedding,
                    user_id=user_id,
                    top_k=candidate_k,
                    filters=filters
                )
                all_vector_results.extend(v_results)
            except Exception as e:
                logger.error(f"Vector search failed for query '{q}': {e}")

            # 1b. BM25 Search
            try:
                b_results = await self.memory_repo.search_by_text(
                    query_text=q,
                    user_id=user_id,
                    top_k=candidate_k,
                    filters=filters
                )
                all_bm25_results.extend(b_results)
            except Exception as e:
                logger.error(f"BM25 search failed for query '{q}': {e}")

        if not all_vector_results and not all_bm25_results:
            return []

        # 2. Compute RRF Scores
        # Map memory_id -> score
        scores: Dict[str, float] = {}
        # Map memory_id -> Memory object
        memories: Dict[str, Memory] = {}

        # Process Vector Results (Deduplicate first to handle multiple expansions returning same result)
        seen_vector_ids = set()
        unique_vector_results = []
        for m in all_vector_results:
            if m.id not in seen_vector_ids:
                seen_vector_ids.add(m.id)
                unique_vector_results.append(m)

        for rank, memory in enumerate(unique_vector_results):
            memories[memory.id] = memory
            scores[memory.id] = scores.get(memory.id, 0.0) + \
                (vector_weight * (1.0 / (rrf_k + rank + 1)))

        # Process BM25 Results
        seen_bm25_ids = set()
        unique_bm25_results = []
        for m in all_bm25_results:
            if m.id not in seen_bm25_ids:
                seen_bm25_ids.add(m.id)
                unique_bm25_results.append(m)

        for rank, memory in enumerate(unique_bm25_results):
            memories[memory.id] = memory
            scores[memory.id] = scores.get(memory.id, 0.0) + \
                (bm25_weight * (1.0 / (rrf_k + rank + 1)))

        # 3. Sort by Score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # 4. Return top_k results
        final_results = [memories[mid] for mid in sorted_ids[:top_k]]

        # 5. Log search session
        if self.db_client:
             try:
                await self.db_client.create_search_session({
                    "user_id": user_id,
                    "query": query,
                    "expanded_queries": expanded_queries,
                    "filters": filters,
                    "results_count": len(final_results),
                    "metadata": {"rrf_k": rrf_k}
                })
             except Exception as e:
                 logger.warning(f"Failed to log search session: {e}")

        return final_results
