from typing import List, Dict, Any, Optional
import logging
import asyncio
from khala.domain.memory.repository import MemoryRepository
from khala.domain.ports.embedding_service import EmbeddingService
from khala.domain.memory.entities import Memory, EmbeddingVector
from khala.application.services.query_expansion_service import QueryExpansionService
from khala.application.services.intent_classifier import IntentClassifier
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
        db_client: Optional[SurrealDBClient] = None,
        intent_classifier: Optional[IntentClassifier] = None
    ):
        self.memory_repo = memory_repository
        self.embedding_service = embedding_service
        self.query_expansion_service = query_expansion_service
        self.db_client = db_client
        self.intent_classifier = intent_classifier

        # Try to initialize intent classifier if not provided but query expansion service is available
        if not self.intent_classifier and self.query_expansion_service and hasattr(self.query_expansion_service, 'gemini_client'):
            self.intent_classifier = IntentClassifier(self.query_expansion_service.gemini_client)

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
        geo_weight: float = 1.0,
        expand_query: bool = False,
        enable_graph_reranking: bool = False,
        geospatial: Optional[Dict[str, float]] = None
        enable_ensemble: bool = False
        language: str = "en",
        proximity_search: Optional[Dict[str, Any]] = None
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
            geo_weight: Weight for Geospatial search results (default 1.0).
            enable_graph_reranking: Whether to apply graph distance reranking (Strategy 121).
            geospatial: Optional dict with 'lat', 'lon', 'radius_km'.
            expand_query: Whether to expand the query.
            enable_graph_reranking: Whether to apply graph distance reranking (Strategy 121).
            enable_ensemble: Whether to use secondary embedding model (Strategy 89).
            language: The language of the query (default "en"). Strategy 95.
            proximity_search: Optional config for proximity search (Strategy 97).
                              Format: {"terms": ["term1", "term2"], "window": 5}

        Returns:
            List of unique Memory objects sorted by RRF score.
        """
        # 0. Intent Classification (Task 30)
        intent = "Analysis" # Default
        if self.intent_classifier:
            intent = await self.intent_classifier.classify(query)
            logger.debug(f"Query intent classified as: {intent}")

        # 0. Query Expansion
        expanded_queries = [query]
        # Strategy 95: Multilingual Search - Translation Layer
        # If language is not English, translate query before vector embedding.
        # We assume content is predominantly English or mapped to English embedding space.

        queries_for_vector = [query]
        queries_for_bm25 = [query]

        if language and language.lower() not in ["en", "english"]:
            # Check if embedding service or gemini client is available for translation
            # We need access to GeminiClient.
            # Ideally EmbeddingService might have it, or we use a separate translator service.
            # But here we only have embedding_service.
            # We can try to cast embedding_service.client if it exists, or check self.query_expansion_service.gemini_client

            gemini_client = None
            if self.query_expansion_service and hasattr(self.query_expansion_service, 'gemini_client'):
                gemini_client = self.query_expansion_service.gemini_client

            # If we found a client, translate
            if gemini_client and hasattr(gemini_client, 'translate_text'):
                try:
                    translated_query = await gemini_client.translate_text(query, target_language="English")
                    logger.info(f"Translated query '{query}' to '{translated_query}' for search")
                    queries_for_vector = [translated_query]
                    # We might want to keep original for BM25 if content is mixed language
                    queries_for_bm25.append(translated_query)
                except Exception as e:
                    logger.warning(f"Translation failed: {e}")

        # 0. Query Expansion (on the English/Vector query)
        expanded_queries = queries_for_vector
        if expand_query and self.query_expansion_service:
            # We expand the primary vector query
            expanded = await self.query_expansion_service.expand_query(queries_for_vector[0])
            expanded_queries.extend(expanded)
            # Ensure uniqueness
            expanded_queries = list(set(expanded_queries))

        # 1. Fetch candidates in parallel for all queries
        # We fetch top_k * 2 candidates from each source to ensure good fusion overlap
        candidate_k = top_k * 2

        all_vector_results: List[Memory] = []
        all_bm25_results: List[Memory] = []
        all_geo_results: List[Memory] = []
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

        async def _fetch_geo() -> List[Memory]:
            if not geospatial:
                return []
            try:
                radius = geospatial.get("radius_km", 50.0)
                lat = geospatial.get("lat")
                lon = geospatial.get("lon")
                if lat is None or lon is None:
                    return []

                results_with_dist = await self.memory_repo.search_by_location(
                    location={"lat": lat, "lon": lon},
                    radius_km=radius,
                    user_id=user_id,
                    top_k=candidate_k,
                    filters=filters
                )
                return [m for m, d in results_with_dist]
            except Exception as e:
                logger.error(f"Geospatial search failed: {e}")
                return []

        # Gather all tasks: 2 tasks per query (Vector + BM25) + 1 Geo task
        # Gather all tasks
        tasks = []
        # Vector search uses expanded_queries (which includes translated query)
        for q in expanded_queries:
            tasks.append(_fetch_vector(q, field="embedding"))
            tasks.append(_fetch_vector(q))

        # BM25 uses queries_for_bm25 (original + translated)
        # We don't necessarily want to run BM25 on all expanded queries as they might be synonyms
        # and BM25 is better with exact terms. But if expansion adds keywords, it's good.
        # For simplicity, let's use expanded_queries for BM25 too, plus original if not in it.

        bm25_queries = list(set(queries_for_bm25 + expanded_queries))
        for q in bm25_queries:
            tasks.append(_fetch_bm25(q))
            if enable_ensemble:
                tasks.append(_fetch_vector(q, field="embedding_secondary"))

        # Geo search is query independent (for now)
        tasks.append(_fetch_geo())

        results = await asyncio.gather(*tasks)

        # Separate results back into vector and bm25 lists
        # Order is [V1, B1, V2, B2, ..., Geo]
        geo_results_idx = len(expanded_queries) * 2

        for i in range(0, geo_results_idx, 2):
        # Separate results
        # If ensemble: [V1, B1, E1, V2, B2, E2 ...]
        # If not: [V1, B1, V2, B2 ...]

        step = 3 if enable_ensemble else 2

        for i in range(0, len(results), step):
            all_vector_results.extend(results[i])
            all_bm25_results.extend(results[i+1])
            if enable_ensemble:
                all_ensemble_results.extend(results[i+2])
        # Separate results back into vector and bm25 lists
        # Order is:
        # [V_1, V_2, ..., V_n, B_1, B_2, ..., B_m]

        num_vector_queries = len(expanded_queries)

        all_geo_results = results[geo_results_idx]

        if not all_vector_results and not all_bm25_results:
        for i, res in enumerate(results):
            if i < num_vector_queries:
                all_vector_results.extend(res)
            else:
                all_bm25_results.extend(res)

        if not all_vector_results and not all_bm25_results and not all_ensemble_results:
            return []

        # 2. Compute RRF Scores
        scores: Dict[str, float] = {}
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

        # Process Geo Results
        seen_geo_ids = set()
        unique_geo_results = []
        for m in all_geo_results:
             if m.id not in seen_geo_ids:
                 seen_geo_ids.add(m.id)
                 unique_geo_results.append(m)

        for rank, memory in enumerate(unique_geo_results):
            memories[memory.id] = memory
            scores[memory.id] = scores.get(memory.id, 0.0) + \
                (geo_weight * (1.0 / (rrf_k + rank + 1)))

        # 3. Sort by Score
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
        # 4. Contextual Search (Proximity) - Strategy 97
        # Filter/Rerank based on proximity of terms
        # This acts as a filter on the sorted candidates

        candidates = [memories[mid] for mid in sorted_ids]

        if proximity_search:
            terms = proximity_search.get("terms", [])
            window = proximity_search.get("window", 10)

            if terms and len(terms) >= 2:
                proximity_filtered = []
                for m in candidates:
                    content_lower = m.content.lower()
                    words = content_lower.split()

                    # Check if all terms are present
                    term_indices = []
                    all_present = True
                    for term in terms:
                        term_lower = term.lower()
                        if term_lower not in content_lower: # Fast check
                            all_present = False
                            break
                        # Get all indices of term
                        indices = [i for i, w in enumerate(words) if term_lower in w]
                        if not indices:
                            all_present = False
                            break
                        term_indices.append(indices)

                    if not all_present:
                        continue

                    # Check distance between any pair of different terms
                    # We need to find if there exists a set of indices (one for each term)
                    # such that max(indices) - min(indices) <= window

                    # Simplified check for 2 terms:
                    if len(terms) == 2:
                        found_proximity = False
                        for i1 in term_indices[0]:
                            for i2 in term_indices[1]:
                                if abs(i1 - i2) <= window:
                                    found_proximity = True
                                    break
                            if found_proximity: break
                        if found_proximity:
                            proximity_filtered.append(m)
                    else:
                        # For > 2 terms, it's more complex (smallest window containing all)
                        # We'll just check if they are all within window range of the first term occurrence
                        # This is a basic approximation
                        found_proximity = False
                        # Flatten all indices
                        all_idxs = sorted([idx for sublist in term_indices for idx in sublist])

                        # Sliding window over indices
                        for i in range(len(all_idxs) - len(terms) + 1):
                            subset = all_idxs[i:i+len(terms)]
                            if subset[-1] - subset[0] <= window:
                                # Check if this subset covers all terms? Not necessarily unique terms
                                # But it's a good heuristic for "dense cluster of terms"
                                found_proximity = True
                                break

                        if found_proximity:
                            proximity_filtered.append(m)

                # Replace candidates with filtered list
                # We might want to just boost them instead of hard filter, but "Search" usually implies filtering
                candidates = proximity_filtered

        # 5. Graph Distance Reranking (Strategy 121)
        # If enabled, we boost results that are 1-hop connected to the top result (anchor)
        # or connected to an "active" concept in the query (if we had entity linking).
        # For now, we'll implement a simple "Anchor Point" boost:
        # If result B is connected to result A (where A is high ranking), boost B.

        final_results = candidates

        client_to_use = self.db_client or (self.memory_repo.client if hasattr(self.memory_repo, 'client') else None)

        if enable_graph_reranking and client_to_use and final_results:
            try:
                anchor_id = final_results[0].id
                anchor_episode = final_results[0].episode_id
                connected_ids = set()
                clean_anchor_id = anchor_id.split(":")[1] if ":" in anchor_id else anchor_id

                query_graph = """
                SELECT from_entity_id, to_entity_id FROM relationship
                WHERE (from_entity_id = $anchor OR to_entity_id = $anchor)
                AND (valid_to IS NONE OR valid_to > time::now())
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
                        "intent": intent  # Log intent
                    }
                })
            except Exception as e:
                logger.warning(f"Failed to log search session: {e}")

        return final_results

    async def search_cross_modal(
        self,
        query: str,
        user_id: str,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Memory]:
        """
        Perform cross-modal search (Text -> Image).

        Uses the text query to search against 'embedding_visual' field of memories
        (which stores image embeddings) or searches standard embeddings but filters for images.

        Args:
            query: The search query string.
            user_id: The ID of the user performing the search.
            top_k: Number of results to return.
            filters: Optional filters.

        Returns:
            List of Memory objects (expected to be images).
        """
        try:
            # 1. Generate text embedding for the query
            # We assume the embedding model for text queries is compatible with
            # the visual embeddings space (Multimodal model)
            embedding_values = await self.embedding_service.get_embedding(query)
            embedding = EmbeddingVector(values=embedding_values)

            # 2. Add filter for images
            # Images are stored with metadata.type = 'image' (from MultimodalService)
            # OR we can check if embedding_visual is not null.

            # Construct filters
            image_filters = filters or {}
            # We can't easily modify the input dict if we want to be safe, so copy
            image_filters = image_filters.copy()

            # We enforce looking for images.
            # Assuming 'metadata.type' is indexed or efficient enough, or we use a custom query.
            # Strategy 78 mentions 'embedding_visual'.

            # If the architecture uses a shared embedding space (like Gemini),
            # text query embedding can match image embedding.
            # If 'embedding_visual' field is used specifically for visual vectors:

            query_sql = """
            SELECT * FROM memory
            WHERE user_id = $user_id
            AND (metadata.type = 'image' OR embedding_visual IS NOT NONE)
            AND vector::similarity::cosine(embedding_visual OR embedding, $query_vec) > $threshold
            ORDER BY vector::similarity::cosine(embedding_visual OR embedding, $query_vec) DESC
            LIMIT $limit;
            """

            # However, the Repository `search_by_vector` might not target `embedding_visual`.
            # We might need to execute a custom query here or rely on `search_by_vector` if `embedding` field holds it.
            # In `MultimodalService`, we see `embedding` field is not explicitly set to a visual embedding
            # (it sets content, tier, etc., but embedding is generated by repo if not provided).
            # If `MultimodalService` relied on repo auto-embedding the DESCRIPTION, then it's text-to-text search.
            # But the requirement is "Cross-Modal Retrieval: Text-to-image search using existing Multi-Modal embeddings".

            # If we assume we have 'embedding_visual' populated (Strategy 78), we should target it.
            # If not, we search against standard embedding but filter for type=image.

            # Let's try to use a custom query for specific 'embedding_visual' if available,
            # otherwise fall back to repo search with type='image'.

            # Using repository search with filter is safer/easier if standard embedding is good enough.
            # But "Cross-Modal" implies using the multimodal capabilities.

            # Let's assume we want to filter by type='image'
            image_filters['metadata.type'] = 'image'

            results = await self.memory_repo.search_by_vector(
                embedding=embedding,
                user_id=user_id,
                top_k=top_k,
                filters=image_filters
            )

            return results

        except Exception as e:
            logger.error(f"Cross-modal search failed for '{query}': {e}")
            return []
