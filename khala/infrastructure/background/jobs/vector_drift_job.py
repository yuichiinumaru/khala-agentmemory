import logging
from typing import Dict, Any, List, Optional
import numpy as np

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.ports.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)

class VectorDriftJob:
    """Background job to detect vector drift by re-embedding content."""

    def __init__(self, db_client: SurrealDBClient, embedding_service: EmbeddingService):
        self.db_client = db_client
        self.embedding_service = embedding_service

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the drift detection job.

        Payload options:
        - sample_size: int (default 100)
        - threshold: float (default 0.95) - if similarity is below this, it's drift.
        """
        sample_size = payload.get("sample_size", 100)
        threshold = payload.get("threshold", 0.95)

        logger.info(f"Starting Vector Drift Job. Sample size: {sample_size}")

        # 1. Fetch random sample of memories that have embeddings
        # We use ORDER BY rand() to get a random sample if supported, otherwise just LIMIT
        query = f"""
        SELECT id, content, embedding
        FROM memory
        WHERE embedding IS NOT NONE
        LIMIT {sample_size};
        """

        memories = []
        try:
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query)
                # Handle SurrealDB response format: usually list of results
                if response and isinstance(response, list):
                    # Check if response[0] is a result object or dict
                    first = response[0]
                    if isinstance(first, dict) and 'result' in first:
                         memories = first['result']
                    else:
                         memories = response
                elif response and isinstance(response, dict):
                    memories = response.get('result', [])
        except Exception as e:
            logger.error(f"Failed to fetch memories: {e}")
            return {"processed": 0, "error": str(e)}

        if not memories:
            return {
                "processed": 0,
                "drift_detected": False,
                "message": "No memories found with embeddings."
            }

        total_drift = 0.0
        drift_count = 0
        min_similarity = 1.0
        max_drift_id = None

        processed = 0
        for mem in memories:
            content = mem.get("content")
            old_embedding = mem.get("embedding")
            mem_id = mem.get("id")

            if not content or not old_embedding:
                continue

            # 2. Generate new embedding
            try:
                new_embedding = await self.embedding_service.get_embedding(content)
            except Exception as e:
                logger.error(f"Failed to generate embedding for {mem_id}: {e}")
                continue

            # 3. Compare (Cosine Similarity)
            vec_a = np.array(old_embedding, dtype=np.float32)
            vec_b = np.array(new_embedding, dtype=np.float32)

            norm_a = np.linalg.norm(vec_a)
            norm_b = np.linalg.norm(vec_b)

            if norm_a == 0 or norm_b == 0:
                logger.warning(f"Zero vector found for {mem_id}")
                continue

            similarity = float(np.dot(vec_a, vec_b) / (norm_a * norm_b))

            # Clip for numerical stability
            similarity = max(-1.0, min(1.0, similarity))

            drift = 1.0 - similarity
            total_drift += drift

            if similarity < min_similarity:
                min_similarity = similarity
                max_drift_id = mem_id

            if similarity < threshold:
                drift_count += 1
                logger.warning(f"Drift detected for {mem_id}: similarity={similarity:.4f}")

            processed += 1

        avg_drift = total_drift / processed if processed > 0 else 0.0

        result = {
            "processed": processed,
            "drift_count": drift_count,
            "avg_drift": avg_drift,
            "min_similarity": min_similarity,
            "max_drift_mem_id": max_drift_id,
            "drift_detected": drift_count > 0
        }

        logger.info(f"Vector Drift Job Completed: {result}")
        return result
