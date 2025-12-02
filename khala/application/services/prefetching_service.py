from typing import List, Dict, Any, Optional
import logging
import json
import asyncio
from cachetools import TTLCache
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.application.utils import parse_json_safely

logger = logging.getLogger(__name__)

class PredictivePrefetcher:
    """
    Service for Intent-Based Prefetching (Strategy 153).
    Predicts and pre-loads related memories based on current intent.
    """
    def __init__(self, gemini_client: GeminiClient, db_client: SurrealDBClient):
        self.gemini_client = gemini_client
        self.db_client = db_client
        # Bounded cache with TTL to prevent memory leaks (Reviewer Feedback)
        # Max 1000 items, expires in 5 minutes
        self._cache = TTLCache(maxsize=1000, ttl=300)

    async def prefetch_related_content(self, user_id: str, current_query: str, current_intent: str) -> Dict[str, Any]:
        """
        Predict what the user might ask next and pre-fetch relevant memories.

        Args:
            user_id: The user ID.
            current_query: The user's current query.
            current_intent: The classified intent of the query.

        Returns:
            Dictionary containing predicted next queries and pre-fetched memory IDs.
        """
        try:
            # 1. Predict likely next steps
            predictions = await self._predict_next_queries(current_query, current_intent)

            if not predictions:
                return {"predicted_queries": [], "prefetched_count": 0}

            # 2. Asynchronously fetch related memories for these predictions
            tasks = []
            queries_to_fetch = []

            for query in predictions:
                cache_key = f"prefetch:{user_id}:{query}"
                if cache_key not in self._cache:
                    queries_to_fetch.append(query)
                    tasks.append(self.db_client.search_memories_by_bm25(
                        query_text=query,
                        user_id=user_id,
                        top_k=3
                    ))

            if not tasks:
                return {
                    "predicted_queries": predictions,
                    "prefetched_count": 0,
                    "status": "all_cached"
                }

            results = await asyncio.gather(*tasks, return_exceptions=True)

            count = 0

            for i, result in enumerate(results):
                query_key = queries_to_fetch[i]
                cache_key = f"prefetch:{user_id}:{query_key}"

                if isinstance(result, list):
                    # Cache these results
                    self._cache[cache_key] = result
                    count += len(result)
                elif isinstance(result, Exception):
                    logger.warning(f"Prefetch failed for query '{query_key}': {result}")

            return {
                "predicted_queries": predictions,
                "prefetched_count": count,
                "debug_info": f"Prefetched {count} items for {len(queries_to_fetch)} new predictions."
            }

        except Exception as e:
            logger.error(f"Prefetching failed: {e}")
            return {"error": str(e)}

    async def _predict_next_queries(self, query: str, intent: str) -> List[str]:
        """Use LLM to predict 3 likely follow-up queries."""
        prompt = f"""
        User Query: "{query}"
        Identified Intent: "{intent}"

        Based on this query and intent, predict 3 likely follow-up questions or related topics the user might ask about next.
        Return ONLY a JSON list of strings.

        Example: ["related topic 1", "follow up question", "deeper detail"]
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="prediction", # Custom task type
                temperature=0.3
            )

            predictions = parse_json_safely(response.get("content", ""))
            if isinstance(predictions, list):
                return predictions[:3]
            return []

        except Exception as e:
            logger.error(f"Prediction failed: {e}")
            return []
