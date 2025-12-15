from typing import List, Dict, Any, Optional
import logging
import asyncio
import re
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

    def _calculate_proximity_score(self, content: str, query_terms: List[str], window_size: int = 10) -> float:
        """
        Calculate a score based on how close query terms are in the content.
        Strategy 97: Contextual Search (Proximity).
        """
        if not content or len(query_terms) < 2:
            return 0.0

        # Normalize
        text = content.lower()
        terms = [t.lower() for t in query_terms if len(t) > 2] # Ignore short words

        if len(terms) < 2:
            return 0.0

        # Find positions of all terms
        positions = []
        for term in terms:
            term_positions = [m.start() for m in re.finditer(re.escape(term), text)]
            if not term_positions:
                # If a significant term is missing, proximity doesn't apply for the full set
                # But we can check for partial proximity if we have at least 2 other terms
                continue
            positions.append(term_positions)

        if len(positions) < 2:
            return 0.0

        # Check minimum distance between any pair of different terms
        min_dist = float('inf')
        found_pair = False

        for i in range(len(positions)):
            for j in range(i + 1, len(positions)):
                pos_list_a = positions[i]
                pos_list_b = positions[j]

                for p_a in pos_list_a:
                    for p_b in pos_list_b:
                        dist = abs(p_a - p_b)
                        if dist < min_dist:
                            min_dist = dist
                            found_pair = True

        if not found_pair:
            return 0.0

        # Convert char distance to approx word distance (avg 6 chars/word incl space)
        word_dist = min_dist / 6.0

        if word_dist <= window_size:
            # Boost score: closer is better.
            # Max boost 0.3 for very close, decaying to 0 at window_size
            return 0.3 * (1.0 - (word_dist / window_size))

        return 0.0

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
        auto_detect_intent: bool = True,
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

        # 0.5 Multilingual Support (Strategy 95)
        search_query = query
        if self.translation_service:
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
        # Strategy 123: Parallel Search Execution
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
        scores: Dict[str, float] = {}
        memories: Dict[str, Memory] = {}

        # Process Vector Results
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

        final_results = [memories[mid] for mid in sorted_ids]

        # Access client safely
        client_to_use = self.db_client
        if not client_to_use and hasattr(self.memory_repo, 'client'):
            client_to_use = self.memory_repo.client

        # 4. Contextual Boosting (Strategy 97)
        # Apply boosts based on context (time, location, etc.)
        context_boost_scores = [0.0] * len(final_results)

        # Pre-calculate query terms for proximity check
        query_terms = search_query.split()

        if context:
            try:
                from datetime import datetime
                # Temporal Proximity
                current_time = context.get('current_time')
                if current_time:
                    if isinstance(current_time, str):
                        current_time = datetime.fromisoformat(current_time)

                    for i, m in enumerate(final_results):
                        if m.created_at:
                            age_seconds = (current_time - m.created_at).total_seconds()
                            if age_seconds < 3600: # 1 hour
                                context_boost_scores[i] += 0.2
                            elif age_seconds < 86400: # 1 day
                                context_boost_scores[i] += 0.1

                # Episode Proximity
                active_episode_id = context.get('episode_id')
                if active_episode_id:
                     for i, m in enumerate(final_results):
                         if m.episode_id == active_episode_id:
                             context_boost_scores[i] += 0.15

            except Exception as e:
                logger.warning(f"Contextual boosting failed: {e}")

        # Proximity Logic (Task 97: Contextual Search Proximity)
        # We calculate proximity score for every result
        for i, m in enumerate(final_results):
            if m.content:
                prox_score = self._calculate_proximity_score(m.content, query_terms)
                if prox_score > 0:
                    context_boost_scores[i] += prox_score

        if (enable_graph_reranking and client_to_use and final_results) or any(s > 0 for s in context_boost_scores):
            try:
                anchor_id = final_results[0].id
                anchor_episode = final_results[0].episode_id
                connected_ids = set()

                if enable_graph_reranking:
                    clean_anchor_id = anchor_id
                    if ":" in clean_anchor_id:
                        clean_anchor_id = clean_anchor_id.split(":")[1]

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
                for i, m in enumerate(final_results):
                    boost_score = context_boost_scores[i]

                    if anchor_episode and m.episode_id == anchor_episode:
                        boost_score += 0.15

                    clean_m_id = m.id.split(":")[1] if ":" in m.id else m.id
                    if clean_m_id in connected_ids:
                        boost_score += 0.10

                    reranked_scores.append(boost_score)

                zipped = list(zip(final_results, reranked_scores))
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
