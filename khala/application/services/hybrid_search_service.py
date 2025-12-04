from typing import List, Dict, Any, Optional
import logging
import asyncio
from khala.domain.memory.repository import MemoryRepository
from khala.domain.ports.embedding_service import EmbeddingService
from khala.domain.memory.entities import Memory, EmbeddingVector
from khala.application.services.query_expansion_service import QueryExpansionService
from khala.application.services.intent_classifier import IntentClassifier, QueryIntent
from khala.application.services.translation_service import TranslationService
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
        intent_classifier: Optional[IntentClassifier] = None,
        translation_service: Optional[TranslationService] = None,
        db_client: Optional[SurrealDBClient] = None
    ):
        self.memory_repo = memory_repository
        self.embedding_service = embedding_service
        self.query_expansion_service = query_expansion_service
        self.intent_classifier = intent_classifier
        self.translation_service = translation_service
        self.db_client = db_client

    def get_search_params_for_intent(self, intent: str) -> Dict[str, Any]:
        """
        Returns optimized search parameters based on query intent.
        """
        params = {
            "vector_weight": 1.0,
            "bm25_weight": 1.0,
            "top_k": 10,
            "enable_graph_reranking": False
        }

        if intent == QueryIntent.FACTUAL.value:
            # Boost BM25 for exact matches, disable graph for speed
            params["bm25_weight"] = 1.5
            params["vector_weight"] = 0.5
            params["top_k"] = 5

        elif intent == QueryIntent.ANALYSIS.value:
            # Boost Vector for semantic understanding, enable graph for context
            params["vector_weight"] = 1.5
            params["bm25_weight"] = 0.5
            params["top_k"] = 20
            params["enable_graph_reranking"] = True

        elif intent == QueryIntent.SUMMARY.value:
            # Balanced, but more results
            params["top_k"] = 15

        elif intent == QueryIntent.CREATIVE.value:
            # High vector weight for inspiration
            params["vector_weight"] = 1.8
            params["bm25_weight"] = 0.2
            params["top_k"] = 15

        return params

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
        auto_detect_intent: bool = False,
        context: Optional[Dict[str, Any]] = None
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
            enable_graph_reranking: Whether to apply graph distance reranking (Strategy 121).
            auto_detect_intent: Whether to use IntentClassifier to adjust weights dynamically.
            context: Contextual parameters for boosting (Strategy 97).

        Returns:
            List of unique Memory objects sorted by RRF score.
        """
        # 0. Intent Detection (Optional)
        if auto_detect_intent and self.intent_classifier:
            try:
                intent_res = await self.intent_classifier.classify_intent(query)
                intent = intent_res.get("intent")
                if intent:
                    params = self.get_search_params_for_intent(intent)
                    # Override defaults if they weren't explicitly customized
                    if vector_weight == 1.0 and bm25_weight == 1.0:
                        vector_weight = params.get("vector_weight", vector_weight)
                        bm25_weight = params.get("bm25_weight", bm25_weight)
                        if params.get("enable_graph_reranking"):
                             enable_graph_reranking = True

                    logger.info(f"Auto-detected intent '{intent}'. Adjusted weights: V={vector_weight}, BM25={bm25_weight}")
            except Exception as e:
                logger.warning(f"Auto-intent detection failed: {e}")

        # 0.5 Query Expansion
        expanded_queries = [query]
        # 0. Multilingual Support (Strategy 95)
        # Check if translation is needed
        search_query = query
        if self.translation_service:
            # We only attempt translation if the query seems non-English or we want robust handling
            # Ideally this is user-configurable, but we'll do auto-detect.
            trans_result = await self.translation_service.detect_and_translate(query)
            if trans_result.get("was_translated"):
                search_query = trans_result.get("translated_text")
                logger.info(f"Translated query: '{query}' -> '{search_query}' ({trans_result.get('detected_language')})")

        # 0.1 Query Expansion
        expanded_queries = [search_query]
        if expand_query and self.query_expansion_service:
            expanded_queries = await self.query_expansion_service.expand_query(search_query)

        # 1. Fetch candidates in parallel for all queries
        # We fetch top_k * 2 candidates from each source to ensure good fusion overlap
        candidate_k = top_k * 2

        all_vector_results: List[Memory] = []
        all_bm25_results: List[Memory] = []

        async def _fetch_vector(q_text: str) -> List[Memory]:
            try:
                embedding = await self.embedding_service.get_embedding(q_text)
                # embedding is now an EmbeddingVector object
                return await self.memory_repo.search_by_vector(
                    embedding=embedding,
                    user_id=user_id,
                    top_k=candidate_k,
                    filters=filters
                )
            except Exception as e:
                logger.error(f"Vector search failed for query '{q_text}': {e}")
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

        # Gather all tasks: 2 tasks per query (Vector + BM25)
        tasks = []
        for q in expanded_queries:
            tasks.append(_fetch_vector(q))
            tasks.append(_fetch_bm25(q))

        results = await asyncio.gather(*tasks)

        # Separate results back into vector and bm25 lists
        # Order is [V1, B1, V2, B2, ...]
        for i in range(0, len(results), 2):
            all_vector_results.extend(results[i])
            all_bm25_results.extend(results[i+1])

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

        # 4. Graph Distance Reranking (Strategy 121)
        # If enabled, we boost results that are 1-hop connected to the top result (anchor)
        # or connected to an "active" concept in the query (if we had entity linking).
        # For now, we'll implement a simple "Anchor Point" boost:
        # If result B is connected to result A (where A is high ranking), boost B.

        final_results = [memories[mid] for mid in sorted_ids]

        # Access client safely (prefer self.memory_repo.client if db_client not set)
        client_to_use = self.db_client
        if not client_to_use and hasattr(self.memory_repo, 'client'):
            client_to_use = self.memory_repo.client

        # 4. Contextual Boosting (Strategy 97)
        # Apply boosts based on context (time, location, etc.)
        context_boost_scores = [0.0] * len(final_results)
        if context:
            try:
                from datetime import datetime
                # Temporal Proximity
                current_time = context.get('current_time')
                if current_time:
                     # If current_time is passed as datetime
                    if isinstance(current_time, str):
                        current_time = datetime.fromisoformat(current_time)

                    for i, m in enumerate(final_results):
                        # Boost recent memories
                        if m.created_at:
                            age_seconds = (current_time - m.created_at).total_seconds()
                            if age_seconds < 3600: # 1 hour
                                context_boost_scores[i] += 0.2
                            elif age_seconds < 86400: # 1 day
                                context_boost_scores[i] += 0.1

                # Location Proximity (if both have location)
                # This requires calculating distance, which is expensive here.
                # We assume SurrealDB handled geospatial filtering if 'filters' were used.
                # Here we might just boost if location metadata matches vaguely.

                # Boost if in same episode
                active_episode_id = context.get('episode_id')
                if active_episode_id:
                     for i, m in enumerate(final_results):
                         if m.episode_id == active_episode_id:
                             context_boost_scores[i] += 0.15

            except Exception as e:
                logger.warning(f"Contextual boosting failed: {e}")


        if (enable_graph_reranking and client_to_use and final_results) or any(s > 0 for s in context_boost_scores):
            try:
                # Use the top result as the "Anchor"
                anchor_id = final_results[0].id

                # Fetch connected entities/memories for the anchor
                # 1. Direct connections via Relationship table (if anchor is an Entity ID or Memory ID tracked in graph)
                # 2. Shared Episode ID (Strategy 118)

                anchor_episode = final_results[0].episode_id
                connected_ids = set()

                if enable_graph_reranking:
                    # If we had Memory-Memory links in relationship table, we could query them.
                    # Assuming 'relationship' table links entities. If Memory IDs are used as Entity IDs or
                    # mapped, we can query. For now, we'll try to fetch direct neighbors.

                    # We need to handle the ID format (strip 'memory:' if present)
                    clean_anchor_id = anchor_id
                    if ":" in clean_anchor_id:
                        clean_anchor_id = clean_anchor_id.split(":")[1]

                    query_graph = """
                    SELECT from_entity_id, to_entity_id FROM relationship
                    WHERE from_entity_id = $anchor OR to_entity_id = $anchor
                    LIMIT 50;
                    """

                    # We use a raw query via client if possible, or skip if client doesn't expose raw query easily here
                    # accessing client_to_use.get_connection()
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

                # Apply Boosting
                # Logic:
                # 1. Same Episode: +15% score
                # 2. Graph Neighbor: +10% score
                # 3. Context Boost: +Variable

                reranked_scores = []
                for i, m in enumerate(final_results):
                    # Base score is inverted rank (higher is better)
                    # We can't easily modify the RRF score directly as it's not passed down.
                    # But we can re-sort.

                    boost_score = context_boost_scores[i]

                    # Episode Boost (if not already handled by context)
                    if anchor_episode and m.episode_id == anchor_episode:
                        boost_score += 0.15

                    # Graph Boost
                    clean_m_id = m.id.split(":")[1] if ":" in m.id else m.id
                    if clean_m_id in connected_ids:
                        boost_score += 0.10

                    # We store (boost, original_index) to sort primarily by boost, then keep original order
                    reranked_scores.append(boost_score)

                # Re-sort final_results based on boost + original position preservation
                # We want to keep the original RRF ordering as the base, but bubble up boosted items.
                # A simple way: add boost to a normalized rank score?
                # Or simply: stable sort by boost descending.

                # Combine memory with boost
                zipped = list(zip(final_results, reranked_scores))
                # Sort: primary key = boost (desc), secondary = original index (asc) is implicit in stable sort
                zipped.sort(key=lambda x: x[1], reverse=True)

                final_results = [m for m, score in zipped]

                logger.debug(f"Graph/Context reranking applied. Anchor: {anchor_id}, Connected: {len(connected_ids)}")

            except Exception as e:
                logger.warning(f"Graph reranking failed: {e}")

        # 5. Return top_k results
        final_results = final_results[:top_k]

        # 6. Log search session
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
                        "graph_reranking": enable_graph_reranking
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to log search session: {e}")

        return final_results
