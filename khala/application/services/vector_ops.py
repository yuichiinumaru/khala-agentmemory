"""Advanced Vector Operations Service for KHALA.

This service implements Strategies 79-84 from Module 11.C.2:
- Strategy 79: Vector Quantization
- Strategy 80: Vector Drift Detection
- Strategy 81: Vector Clustering
- Strategy 82: Adaptive Vector Dimensions
- Strategy 83: Vector-Space Anomaly Detection
- Strategy 84: Vector Interpolation
"""

import logging
from typing import List, Dict, Optional, Tuple, Any, Union
import numpy as np
import datetime
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class AdvancedVectorService:
    """Service for advanced vector operations and analytics."""

    def __init__(self, db_client: SurrealDBClient):
        """Initialize service with database client.

        Args:
            db_client: SurrealDBClient instance
        """
        self.db_client = db_client

    def quantize_vector(self, vector: List[float], method: str = "int8") -> List[int]:
        """Implement Strategy 79: Vector Quantization.

        Converts a float vector to a quantized integer representation for storage optimization.
        Currently supports 'int8' scalar quantization mapping [-1.0, 1.0] to [-127, 127].

        Args:
            vector: Input float embedding vector
            method: Quantization method (default: "int8")

        Returns:
            List[int]: Quantized integer vector
        """
        if method == "int8":
            # Assuming normalized vectors in [-1, 1] range for cosine similarity
            # Map -1.0 -> -127, 1.0 -> 127
            vec_np = np.array(vector, dtype=np.float32)
            # Clip to range just in case
            vec_np = np.clip(vec_np, -1.0, 1.0)
            quantized = (vec_np * 127).astype(np.int8)
            return quantized.tolist()
        else:
            raise ValueError(f"Unsupported quantization method: {method}")

    def dequantize_vector(self, quantized_vector: List[int], method: str = "int8") -> List[float]:
        """Reconstruct float vector from quantized representation.

        Args:
            quantized_vector: Input integer vector
            method: Quantization method (default: "int8")

        Returns:
            List[float]: Reconstructed approximate float vector
        """
        if method == "int8":
            vec_np = np.array(quantized_vector, dtype=np.float32)
            return (vec_np / 127.0).tolist()
        else:
            raise ValueError(f"Unsupported quantization method: {method}")

    def reduce_dimensions(self, vector: List[float], target_dim: int) -> List[float]:
        """Implement Strategy 82: Adaptive Vector Dimensions.

        Reduces vector dimensionality via truncation. For embeddings like OpenAI's text-embedding-3,
        truncation is a supported method for dimensionality reduction.

        Args:
            vector: Input float vector
            target_dim: Desired dimension size

        Returns:
            List[float]: Reduced dimension vector (renormalized)
        """
        vec_np = np.array(vector)
        if len(vec_np) <= target_dim:
            return vector

        # Truncate
        reduced = vec_np[:target_dim]

        # Renormalize (L2 norm)
        norm = np.linalg.norm(reduced)
        if norm > 0:
            reduced = reduced / norm

        return reduced.tolist()

    def interpolate_vectors(self, vector_a: List[float], vector_b: List[float], alpha: float = 0.5) -> List[float]:
        """Implement Strategy 84: Vector Interpolation.

        Blends two vectors to find a concept "between" them.

        Args:
            vector_a: First vector
            vector_b: Second vector
            alpha: Blend factor (0.0 = vector_a, 1.0 = vector_b)

        Returns:
            List[float]: Interpolated vector (normalized)
        """
        a = np.array(vector_a)
        b = np.array(vector_b)

        if a.shape != b.shape:
            raise ValueError("Vectors must have same dimensions for interpolation")

        interpolated = (1 - alpha) * a + alpha * b

        # Normalize result
        norm = np.linalg.norm(interpolated)
        if norm > 0:
            interpolated = interpolated / norm

        return interpolated.tolist()

    async def compute_clusters(self, k: int = 10, sample_size: int = 1000) -> Dict[str, Any]:
        """Implement Strategy 81: Vector Clustering.

        Fetches memory vectors, performs K-Means clustering, and stores centroids.

        Args:
            k: Number of clusters
            sample_size: Max number of vectors to fetch for clustering

        Returns:
            Dict containing clustering statistics
        """
        # 1. Fetch vectors from DB
        query = f"SELECT id, embedding FROM memory WHERE embedding IS NOT NONE LIMIT {sample_size};"
        async with self.db_client.get_connection() as conn:
            results = await conn.query(query)

        memories = results if results else []
        if not memories:
            logger.warning("No memories found for clustering")
            return {"status": "no_data"}

        vectors = []
        ids = []
        for mem in memories:
            if mem.get("embedding"):
                vectors.append(mem["embedding"])
                ids.append(mem["id"])

        if len(vectors) < k:
            logger.warning(f"Not enough vectors ({len(vectors)}) for {k} clusters")
            return {"status": "insufficient_data"}

        X = np.array(vectors)

        # 2. Perform KMeans
        kmeans = KMeans(n_clusters=k, random_state=42, n_init=10)
        kmeans.fit(X)

        centroids = kmeans.cluster_centers_
        labels = kmeans.labels_

        # 3. Store Clusters
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()
        cluster_map = {} # map cluster index to DB record

        async with self.db_client.get_connection() as conn:
            # Clear old clusters? Or archive? For now, we create new ones.
            # Strategy: Delete old clusters for simplicity in this implementation,
            # or we could version them.
            await conn.query("DELETE vector_cluster;")

            for i, centroid in enumerate(centroids):
                # Calculate radius (max distance of a point in this cluster)
                cluster_points = X[labels == i]
                if len(cluster_points) > 0:
                    # distance from centroid
                    dists = np.linalg.norm(cluster_points - centroid, axis=1)
                    radius = float(np.max(dists))
                else:
                    radius = 0.0

                record = {
                    "centroid": centroid.tolist(),
                    "radius": radius,
                    "member_count": int(np.sum(labels == i)),
                    "created_at": timestamp,
                    "updated_at": timestamp
                }

                created = await conn.create("vector_cluster", record)
                cluster_map[i] = created[0]["id"]

            # 4. Update Memories with Cluster ID
            # This can be slow for many memories, ideally done in batch or async job
            # For this implementation, we'll update the ones we sampled
            for idx, mem_id in enumerate(ids):
                cluster_idx = labels[idx]
                cluster_record_id = cluster_map[cluster_idx]

                # Update memory
                await conn.query(f"UPDATE {mem_id} SET cluster_id = {cluster_record_id};")

        return {
            "status": "success",
            "clusters_created": k,
            "memories_updated": len(ids)
        }

    async def detect_anomalies(self, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Implement Strategy 83: Vector-Space Anomaly Detection.

        Identifies memories that are far from their cluster centroids.

        Args:
            threshold_std: Number of standard deviations to consider an outlier

        Returns:
            List of anomalous memory records
        """
        # Fetch memories with cluster info
        query = """
        SELECT id, embedding, cluster_id, cluster_id.centroid as centroid, cluster_id.radius as radius
        FROM memory
        WHERE embedding IS NOT NONE AND cluster_id IS NOT NONE;
        """
        async with self.db_client.get_connection() as conn:
            results = await conn.query(query)

        if not results:
            return []

        anomalies = []
        distances = []

        # First pass: calculate all distances to get stats
        processed_results = []
        for mem in results:
            if not mem.get("centroid"): continue

            vec = np.array(mem["embedding"])
            cent = np.array(mem["centroid"])
            dist = float(np.linalg.norm(vec - cent))
            distances.append(dist)
            mem["_dist"] = dist
            processed_results.append(mem)

        if not distances:
            return []

        mean_dist = np.mean(distances)
        std_dist = np.std(distances)
        cutoff = mean_dist + (threshold_std * std_dist)

        # Second pass: identify outliers
        for mem in processed_results:
            if mem["_dist"] > cutoff:
                anomaly_score = (mem["_dist"] - mean_dist) / (std_dist + 1e-9) # simple z-score

                # Update memory with anomaly score
                async with self.db_client.get_connection() as conn:
                    await conn.query(f"UPDATE {mem['id']} SET anomaly_score = {anomaly_score};")

                anomalies.append({
                    "id": mem["id"],
                    "distance": mem["_dist"],
                    "anomaly_score": anomaly_score,
                    "cluster_id": mem["cluster_id"]
                })

        return anomalies

    async def detect_drift(self, model_version: str = "default") -> Dict[str, Any]:
        """Implement Strategy 80: Vector Drift Detection.

        Calculates current distribution statistics and compares with historical baselines.

        Args:
            model_version: The embedding model version tag

        Returns:
            Drift analysis results
        """
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        # Fetch all embeddings
        query = "SELECT embedding FROM memory WHERE embedding IS NOT NONE;"
        async with self.db_client.get_connection() as conn:
            results = await conn.query(query)

        if not results:
            return {"status": "no_data"}

        vectors = [r["embedding"] for r in results]
        X = np.array(vectors)

        # Calculate current stats
        mean_embedding = np.mean(X, axis=0)
        variance = float(np.var(X)) # Scalar variance (trace of covariance / dims or just variance of flattened)
        # Better: average squared distance from mean
        variance = float(np.mean(np.sum((X - mean_embedding)**2, axis=1)))

        # Fetch previous stats
        prev_query = "SELECT * FROM vector_stats ORDER BY window_start DESC LIMIT 1;"
        async with self.db_client.get_connection() as conn:
            prev_results = await conn.query(prev_query)

        drift_score = 0.0
        if prev_results:
            prev = prev_results[0]
            prev_mean = np.array(prev["mean_embedding"])
            # Drift = distance between means
            drift_score = float(np.linalg.norm(mean_embedding - prev_mean))

        # Store new stats
        stat_record = {
            "window_start": timestamp, # Using point in time for simplicity
            "window_end": timestamp,
            "mean_embedding": mean_embedding.tolist(),
            "variance": variance,
            "drift_score": drift_score,
            "sample_count": len(vectors),
            "model_version": model_version
        }

        async with self.db_client.get_connection() as conn:
            await conn.create("vector_stats", stat_record)

        return {
            "drift_score": drift_score,
            "variance": variance,
            "sample_count": len(vectors),
            "status": "drift_detected" if drift_score > 0.1 else "stable" # Arbitrary threshold
        }
