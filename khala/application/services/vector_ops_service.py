"""
Service for advanced vector operations: Interpolation and Anomaly Detection.
Strategies 83 (Anomaly Detection) and 84 (Interpolation).
"""

import logging
import numpy as np
from typing import List, Dict, Any, Optional
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.memory.entities import Memory
from khala.domain.memory.value_objects import EmbeddingVector

logger = logging.getLogger(__name__)

class VectorOpsService:
    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def interpolate_vectors(
        self,
        user_id: str,
        memory_id_1: str,
        memory_id_2: str,
        alpha: float = 0.5,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Generate a "bridge" concept by interpolating between two memory vectors.

        Args:
            user_id: The user ID.
            memory_id_1: ID of the first memory.
            memory_id_2: ID of the second memory.
            alpha: Interpolation factor (0.0 to 1.0). 0.5 is midpoint.
            top_k: Number of results to return.

        Returns:
            List of memories closest to the interpolated vector.
        """
        if not (0.0 <= alpha <= 1.0):
            raise ValueError("Alpha must be between 0.0 and 1.0")

        # Fetch memories
        mem1 = await self.db_client.get_memory(memory_id_1)
        mem2 = await self.db_client.get_memory(memory_id_2)

        if not mem1 or not mem2:
            raise ValueError("One or both memories not found")

        if not mem1.embedding or not mem2.embedding:
            raise ValueError("One or both memories lack embeddings")

        if len(mem1.embedding.values) != len(mem2.embedding.values):
            raise ValueError("Embedding dimensions mismatch")

        # Interpolate
        vec1 = np.array(mem1.embedding.values)
        vec2 = np.array(mem2.embedding.values)

        # Linear interpolation
        interpolated = (1 - alpha) * vec1 + alpha * vec2

        interpolated_list = interpolated.tolist()

        # Create EmbeddingVector (handles validation)
        try:
            target_embedding = EmbeddingVector(interpolated_list)
        except ValueError as e:
            logger.error(f"Interpolated vector validation failed: {e}")
            raise

        # Search
        # We might want to filter out the source memories from results
        results = await self.db_client.search_memories_by_vector(
            embedding=target_embedding,
            user_id=user_id,
            top_k=top_k + 2 # Fetch more to filter out sources
        )

        # Filter out source memories
        # Normalize IDs for comparison (strip 'memory:' prefix if present)
        def normalize_id(mid):
            return str(mid).split(":")[-1]

        target_ids = {normalize_id(memory_id_1), normalize_id(memory_id_2)}

        filtered_results = []
        for r in results:
            rid = normalize_id(r.get('id', ''))
            if rid not in target_ids:
                filtered_results.append(r)

        return filtered_results[:top_k]

    async def detect_anomalies(
        self,
        user_id: str,
        sample_size: int = 100,
        threshold: float = 0.5,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Identify memories that are outliers in the vector space.

        Uses a centroid-based approach:
        1. Fetches a sample of recent memories.
        2. Computes the centroid.
        3. Finds memories furthest from this centroid (low cosine similarity).

        Args:
            user_id: The user ID.
            sample_size: Number of memories to sample for centroid calculation.
            threshold: Similarity threshold (memories with similarity < threshold are returned).
            limit: Max number of outliers to return.

        Returns:
            List of outlier memories.
        """
        # Fetch sample
        sample_memories = await self.db_client.get_latest_memories(user_id, limit=sample_size)

        if not sample_memories:
            return []

        # Extract vectors
        vectors = [m.embedding.values for m in sample_memories if m.embedding]

        if not vectors:
            return []

        # Compute centroid
        # Simple mean of vectors
        vectors_np = np.array(vectors)
        centroid = np.mean(vectors_np, axis=0)

        centroid_list = centroid.tolist()

        # Query for outliers
        outliers = await self.db_client.find_outliers_by_centroid(
            centroid=centroid_list,
            user_id=user_id,
            limit=limit,
            max_similarity=threshold
        )

        return outliers
