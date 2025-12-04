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
        """Implement Strategy 79: Vector Quantization."""
        if method == "int8":
            vec_np = np.array(vector, dtype=np.float32)
            vec_np = np.clip(vec_np, -1.0, 1.0)
            quantized = (vec_np * 127).astype(np.int8)
            return quantized.tolist()
        else:
            raise ValueError(f"Unsupported quantization method: {method}")

    def dequantize_vector(self, quantized_vector: List[int], method: str = "int8") -> List[float]:
        """Reconstruct float vector from quantized representation."""
        if method == "int8":
            vec_np = np.array(quantized_vector, dtype=np.float32)
            return (vec_np / 127.0).tolist()
        else:
            raise ValueError(f"Unsupported quantization method: {method}")

    def reduce_dimensions(self, vector: List[float], target_dim: int) -> List[float]:
        """Implement Strategy 82: Adaptive Vector Dimensions."""
        vec_np = np.array(vector)
        if len(vec_np) <= target_dim:
            return vector

        reduced = vec_np[:target_dim]
        norm = np.linalg.norm(reduced)
        if norm > 0:
            reduced = reduced / norm

        return reduced.tolist()

    def interpolate_vectors(self, vector_a: List[float], vector_b: List[float], alpha: float = 0.5) -> List[float]:
        """Implement Strategy 84: Vector Interpolation."""
        a = np.array(vector_a)
        b = np.array(vector_b)

        if a.shape != b.shape:
            raise ValueError("Vectors must have same dimensions for interpolation")

        interpolated = (1 - alpha) * a + alpha * b
        norm = np.linalg.norm(interpolated)
        if norm > 0:
            interpolated = interpolated / norm

        return interpolated.tolist()

    async def compute_clusters(self, k: int = 10, sample_size: int = 1000) -> Dict[str, Any]:
        """Implement Strategy 81: Vector Clustering (Optimized)."""
        # 1. Fetch vectors
        query = f"SELECT id, embedding FROM memory WHERE embedding IS NOT NONE LIMIT {sample_size};"
        async with self.db_client.get_connection() as conn:
            results = await conn.query(query)

        memories = results if results else []
        if isinstance(memories, list) and len(memories) > 0 and isinstance(memories[0], dict) and 'result' in memories[0]:
             memories = memories[0]['result']

        if not memories:
            logger.warning("No memories found for clustering")
            return {"status": "no_data"}

        vectors = []
        ids = []
        for mem in memories:
            if isinstance(mem, dict) and mem.get("embedding"):
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
        cluster_map = {}

        async with self.db_client.get_connection() as conn:
            await conn.query("DELETE vector_cluster;")

            for i, centroid in enumerate(centroids):
                cluster_points = X[labels == i]
                radius = float(np.max(np.linalg.norm(cluster_points - centroid, axis=1))) if len(cluster_points) > 0 else 0.0

                record = {
                    "centroid": centroid.tolist(),
                    "radius": radius,
                    "member_count": int(np.sum(labels == i)),
                    "created_at": timestamp,
                    "updated_at": timestamp
                }

                created = await conn.create("vector_cluster", record)
                if isinstance(created, list) and len(created) > 0:
                     cluster_map[i] = created[0]["id"]
                elif isinstance(created, dict) and "id" in created:
                     cluster_map[i] = created["id"]

            # 4. Update Memories with Cluster ID (Batch)
            batch_size = 50
            for i in range(0, len(ids), batch_size):
                batch_ids = ids[i:i+batch_size]
                batch_labels = labels[i:i+batch_size]

                queries = []
                params = {}

                for j, mem_id in enumerate(batch_ids):
                    cluster_idx = batch_labels[j]
                    if cluster_idx in cluster_map:
                        cluster_record_id = cluster_map[cluster_idx]
                        # Use parameter binding for ID to prevent injection
                        queries.append(f"UPDATE $id_{j} SET cluster_id = $cid_{j};")
                        params[f"id_{j}"] = mem_id
                        params[f"cid_{j}"] = cluster_record_id

                if queries:
                    await conn.query("\n".join(queries), params)

        return {
            "status": "success",
            "clusters_created": len(cluster_map),
            "memories_updated": len(ids)
        }

    async def detect_anomalies(self, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Implement Strategy 83: Vector-Space Anomaly Detection (Optimized)."""
        query = """
        SELECT id, embedding, cluster_id, cluster_id.centroid as centroid
        FROM memory
        WHERE embedding IS NOT NONE AND cluster_id IS NOT NONE;
        """
        async with self.db_client.get_connection() as conn:
            results = await conn.query(query)

        memories = []
        if isinstance(results, list):
             if len(results) > 0 and isinstance(results[0], dict) and 'result' in results[0]:
                 memories = results[0]['result']
             else:
                 memories = results

        if not memories:
            return []

        anomalies = []
        distances = []
        processed_results = []

        for mem in memories:
            if not isinstance(mem, dict) or not mem.get("centroid"): continue

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

        # Identify outliers
        for mem in processed_results:
            if mem["_dist"] > cutoff:
                anomaly_score = (mem["_dist"] - mean_dist) / (std_dist + 1e-9)

                anomalies.append({
                    "id": mem["id"],
                    "distance": mem["_dist"],
                    "anomaly_score": anomaly_score,
                    "cluster_id": mem["cluster_id"]
                })

        # Batch update anomalies
        if anomalies:
            async with self.db_client.get_connection() as conn:
                batch_size = 50
                for i in range(0, len(anomalies), batch_size):
                    batch = anomalies[i:i+batch_size]
                    queries = []
                    params = {}

                    for j, item in enumerate(batch):
                         queries.append(f"UPDATE $id_{j} SET anomaly_score = $score_{j};")
                         params[f"id_{j}"] = item["id"]
                         params[f"score_{j}"] = item["anomaly_score"]

                    if queries:
                        await conn.query("\n".join(queries), params)

        return anomalies

    async def detect_drift(self, model_version: str = "default") -> Dict[str, Any]:
        """Implement Strategy 80: Vector Drift Detection."""
        timestamp = datetime.datetime.now(datetime.timezone.utc).isoformat()

        query = "SELECT embedding FROM memory WHERE embedding IS NOT NONE;"
        async with self.db_client.get_connection() as conn:
            results = await conn.query(query)

        vectors = []
        if isinstance(results, list):
             if len(results) > 0 and isinstance(results[0], dict) and 'result' in results[0]:
                 items = results[0]['result']
             else:
                 items = results
             vectors = [r["embedding"] for r in items if isinstance(r, dict) and "embedding" in r]

        if not vectors:
            return {"status": "no_data"}

        X = np.array(vectors)
        mean_embedding = np.mean(X, axis=0)
        # Average squared Euclidean distance from the mean (trace of covariance matrix)
        variance = float(np.mean(np.sum((X - mean_embedding)**2, axis=1)))

        prev_query = "SELECT * FROM vector_stats ORDER BY window_start DESC LIMIT 1;"
        async with self.db_client.get_connection() as conn:
            prev_results = await conn.query(prev_query)

        drift_score = 0.0
        if prev_results:
             if isinstance(prev_results, list) and len(prev_results) > 0:
                 if isinstance(prev_results[0], dict) and 'result' in prev_results[0]:
                     prev_items = prev_results[0]['result']
                 else:
                     prev_items = prev_results

                 if prev_items and isinstance(prev_items[0], dict) and "mean_embedding" in prev_items[0]:
                     prev = prev_items[0]
                     prev_mean = np.array(prev["mean_embedding"])
                     drift_score = float(np.linalg.norm(mean_embedding - prev_mean))

        # Save stats
        stat_record = {
            "window_start": timestamp,
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
            "status": "drift_detected" if drift_score > 0.1 else "stable"
        }
