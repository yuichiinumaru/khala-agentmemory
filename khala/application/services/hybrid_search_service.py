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
    Includes Strategy 88 (Feedback-Loop) and Strategy 89 (Vector Ensemble).
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

    async def record_feedback(self, session_id: str, memory_id: str, query_text: str, score: float) -> str:
        """
        Record user feedback for a search result.
        Strategy 88: Feedback-Loop Vectors.

        Args:
            session_id: ID of the search session.
            memory_id: ID of the clicked/rated memory.
            query_text: The search query.
            score: Feedback score (e.g. 1.0 for click, -1.0 for negative, 0.5 for dwell).

        Returns:
            Feedback ID.
        """
        if self.db_client:
            return await self.db_client.create_search_feedback(session_id, memory_id, query_text, score)
        return ""

    async def search(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        rrf_k: int = 60,
        vector_weight: float = 1.0,
        bm25_weight: float = 1.0,
        expand_query: bool = False,
        enable_graph_reranking: bool = False,
        enable_ensemble: bool = False
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
            expand_query: Whether to expand the query.
            enable_graph_reranking: Whether to apply graph distance reranking (Strategy 121).
            enable_ensemble: Whether to use secondary embedding model (Strategy 89).

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
        all_ensemble_results: List[Memory] = [] # For Strategy 89

        async def _fetch_vector(q_text: str, model_id: Optional[str] = None, field: str = "embedding") -> List[Memory]:
            try:
                # If embedding service supports model_id, use it.
                # Assuming get_embedding just uses default unless we change signature.
                # Here we assume we might need to modify EmbeddingService if we want to pass model_id
                # For now, we will assume standard get_embedding works for primary.
                # For secondary, we might need a specific call.

                # HACK: If field is embedding_secondary, we try to use a different model if possible
                # But EmbeddingService interface is generic.
                # We will rely on the fact that if enable_ensemble is True, we probably want to
                # use a different model.

                embedding_values = []
                if field == "embedding_secondary":
                    # Try to get secondary embedding.
                    # If EmbeddingService is GeminiClient, we can access generate_embeddings with model_id
                    if hasattr(self.embedding_service, 'generate_embeddings'):
                         # Use the secondary model defined in ModelRegistry
                         res = await self.embedding_service.generate_embeddings([q_text], model_id="text-embedding-004")
                         if res:
                             embedding_values = res[0]
                else:
                    embedding_values = await self.embedding_service.get_embedding(q_text)

                if not embedding_values:
                    return []

                embedding = EmbeddingVector(values=embedding_values)

                # Use search_memories_by_vector with field_name if available in client
                # Repository might abstract this. If repo doesn't support field selection, we might be limited.
                # Check MemoryRepository signature. It doesn't have field_name.
                # We need to bypass repo or assume repo handles it.
                # Since we updated SurrealDBClient, but MemoryRepository interface is fixed...
                # We should cast repo to concrete implementation or update repo.
                # For this task, let's access client directly if possible for advanced features

                if self.db_client:
                    results = await self.db_client.search_memories_by_vector(
                        embedding=embedding,
                        user_id=user_id,
                        top_k=candidate_k,
                        filters=filters,
                        field_name=field
                    )
                    # Convert dicts to Memory objects
                    return [self.db_client._deserialize_memory(r) for r in results]
                else:
                    # Fallback to repo (only supports primary embedding)
                    if field == "embedding":
                        return await self.memory_repo.search_by_vector(
                            embedding=embedding,
                            user_id=user_id,
                            top_k=candidate_k,
                            filters=filters
                        )
                    return []

            except Exception as e:
                logger.error(f"Vector search failed for query '{q_text}' on field {field}: {e}")
                return []

        async def _fetch_bm25(q_text: str) -> List[Memory]:
            try:
                return await self.memory_repo.search_by_text(
                    query_text=q_text,
                    user_id=user_id,
                    top_k=candidate_k,
                    filters=filters
                )
            except Exception as e:
                logger.error(f"BM25 search failed for query '{q_text}': {e}")
                return []

        # Gather all tasks
        tasks = []
        for q in expanded_queries:
            tasks.append(_fetch_vector(q, field="embedding"))
            tasks.append(_fetch_bm25(q))
            if enable_ensemble:
                tasks.append(_fetch_vector(q, field="embedding_secondary"))

        results = await asyncio.gather(*tasks)

        # Separate results
        # If ensemble: [V1, B1, E1, V2, B2, E2 ...]
        # If not: [V1, B1, V2, B2 ...]

        step = 3 if enable_ensemble else 2

        for i in range(0, len(results), step):
            all_vector_results.extend(results[i])
            all_bm25_results.extend(results[i+1])
            if enable_ensemble:
                all_ensemble_results.extend(results[i+2])

        if not all_vector_results and not all_bm25_results and not all_ensemble_results:
            return []

        # 2. Compute RRF Scores
        scores: Dict[str, float] = {}
        memories: Dict[str, Memory] = {}

        def process_results(results_list, weight):
            seen_ids = set()
            unique_results = []
            for m in results_list:
                if m.id not in seen_ids:
                    seen_ids.add(m.id)
                    unique_results.append(m)

            for rank, memory in enumerate(unique_results):
                memories[memory.id] = memory
                scores[memory.id] = scores.get(memory.id, 0.0) + \
                    (weight * (1.0 / (rrf_k + rank + 1)))

        process_results(all_vector_results, vector_weight)
        process_results(all_bm25_results, bm25_weight)

        if enable_ensemble:
            # Strategy 89: Average scores (or just fuse ranks)
            process_results(all_ensemble_results, vector_weight) # Use same weight for now

        # 3. Apply Feedback-Loop Boosting (Strategy 88)
        if self.db_client:
            try:
                # Fetch feedback for the original query
                feedback_items = await self.db_client.get_feedback_for_query(query)
                feedback_map = {item['memory_id']: item['total_score'] for item in feedback_items}

                for mem_id, boost in feedback_map.items():
                    if mem_id in scores:
                        # Apply boost. A score of 1.0 (one click) is significant in RRF (typical scores are small)
                        # RRF scores are usually < 0.1 per list.
                        # We'll add a scaled boost.
                        scores[mem_id] += (boost * 0.05) # 5% boost per click roughly
                        logger.debug(f"Applied feedback boost {boost} to memory {mem_id}")
            except Exception as e:
                logger.warning(f"Feedback boosting failed: {e}")

        # 4. Sort by Score
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)

        # 5. Graph Distance Reranking (Strategy 121)
        final_results = [memories[mid] for mid in sorted_ids]

        client_to_use = self.db_client or (self.memory_repo.client if hasattr(self.memory_repo, 'client') else None)

        if enable_graph_reranking and client_to_use and final_results:
            try:
                anchor_id = final_results[0].id
                anchor_episode = final_results[0].episode_id
                connected_ids = set()
                clean_anchor_id = anchor_id.split(":")[1] if ":" in anchor_id else anchor_id

                query_graph = """
                SELECT from_entity_id, to_entity_id FROM relationship
                WHERE from_entity_id = $anchor OR to_entity_id = $anchor
                LIMIT 50;
                """

                async with client_to_use.get_connection() as conn:
                    graph_resp = await conn.query(query_graph, {"anchor": clean_anchor_id})
                    if graph_resp and isinstance(graph_resp, list):
                         items = graph_resp
                         if len(graph_resp) > 0 and isinstance(graph_resp[0], dict) and 'result' in graph_resp[0]:
                             items = graph_resp[0]['result']
                         for item in items:
                             if isinstance(item, dict):
                                 if item.get('from_entity_id') != clean_anchor_id:
                                     connected_ids.add(item.get('from_entity_id'))
                                 if item.get('to_entity_id') != clean_anchor_id:
                                     connected_ids.add(item.get('to_entity_id'))

                reranked_scores = []
                for m in final_results:
                    boost_score = 0.0
                    if anchor_episode and m.episode_id == anchor_episode:
                        boost_score += 0.15
                    clean_m_id = m.id.split(":")[1] if ":" in m.id else m.id
                    if clean_m_id in connected_ids:
                        boost_score += 0.10
                    reranked_scores.append(boost_score)

                zipped = list(zip(final_results, reranked_scores))
                zipped.sort(key=lambda x: x[1], reverse=True)
                final_results = [m for m, score in zipped]

            except Exception as e:
                logger.warning(f"Graph reranking failed: {e}")

        # 6. Return top_k results
        final_results = final_results[:top_k]

        # 7. Log search session
        if client_to_use:
            try:
                await client_to_use.create_search_session({
                    "user_id": user_id,
                    "query": query,
                    "expanded_queries": expanded_queries,
                    "filters": filters,
                    "results_count": len(final_results),
                    "metadata": {
                        "rrf_k": rrf_k,
                        "graph_reranking": enable_graph_reranking,
                        "ensemble": enable_ensemble
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to log search session: {e}")

        return final_results
