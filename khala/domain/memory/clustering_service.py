"""Domain service for vector clustering using K-Means.

This service implements K-Means clustering to group memories by vector similarity
and maintain centroids for faster search/navigation.
"""

import numpy as np
from typing import List, Tuple, Dict, Any, Optional
import uuid
from datetime import datetime, timezone
import logging

from .entities import Memory
from .clustering import VectorCentroid
from .value_objects import EmbeddingVector

logger = logging.getLogger(__name__)


class NumpyKMeans:
    """Simple K-Means implementation using NumPy."""

    def __init__(self, n_clusters: int = 10, max_iter: int = 300, tol: float = 1e-4):
        self.n_clusters = n_clusters
        self.max_iter = max_iter
        self.tol = tol
        self.centroids = None

    def fit(self, X: np.ndarray) -> None:
        """Compute k-means clustering.

        Args:
            X: Array of shape (n_samples, n_features)
        """
        n_samples, n_features = X.shape

        if n_samples < self.n_clusters:
            self.n_clusters = n_samples

        # Random initialization
        random_indices = np.random.choice(n_samples, self.n_clusters, replace=False)
        self.centroids = X[random_indices]

        for _ in range(self.max_iter):
            # Assign clusters
            # Compute distances (n_samples, n_clusters)
            # dist = ||X - C||^2 = ||X||^2 + ||C||^2 - 2 X.C^T
            # For cosine similarity (assuming normalized vectors), distance is closely related to 1 - cosine
            # But standard K-Means uses Euclidean. We'll use Euclidean here which works fine on normalized vectors too.

            distances = np.linalg.norm(X[:, np.newaxis] - self.centroids, axis=2)
            labels = np.argmin(distances, axis=1)

            new_centroids = np.zeros((self.n_clusters, n_features))
            for i in range(self.n_clusters):
                cluster_points = X[labels == i]
                if len(cluster_points) > 0:
                    new_centroids[i] = cluster_points.mean(axis=0)
                else:
                    # Re-initialize empty cluster
                    new_centroids[i] = X[np.random.randint(n_samples)]

            # Check convergence
            if np.allclose(self.centroids, new_centroids, atol=self.tol):
                break

            self.centroids = new_centroids

    def predict(self, X: np.ndarray) -> np.ndarray:
        """Predict the closest cluster each sample in X belongs to."""
        if self.centroids is None:
            raise ValueError("KMeans not fitted")

        distances = np.linalg.norm(X[:, np.newaxis] - self.centroids, axis=2)
        return np.argmin(distances, axis=1)


class VectorClusteringService:
    """Service for managing vector clusters and centroids."""

    def __init__(self, db_client: Any):
        self.db_client = db_client

    async def perform_clustering(self, user_id: str, n_clusters: int = 10) -> List[VectorCentroid]:
        """Perform clustering on user memories and update DB."""
        # 1. Fetch all memories with embeddings
        # Note: In a real system we might limit this or process in batches
        # We need a method to get all vectors. For now we use get_memories_by_tier assuming we do it per tier or all.
        # Let's assume we fetch recent memories or all active ones.

        # We'll need a custom query to fetch embeddings efficiently
        query = "SELECT id, embedding FROM memory WHERE user_id = $user_id AND embedding != NONE AND is_archived = false;"

        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, {"user_id": user_id})
            if not response or not isinstance(response, list):
                logger.warning("No memories found for clustering")
                return []

            # Extract list from response (SurrealDB returns list of query results)
            # If single query, response is list of results.
            # If response[0] is dict with 'result', use that.
            memories_data = []
            if len(response) > 0:
                if isinstance(response[0], dict) and 'result' in response[0]:
                    memories_data = response[0]['result']
                elif isinstance(response[0], list):
                    memories_data = response[0]
                else:
                    memories_data = response

        if not memories_data:
            logger.info("No memories with embeddings found.")
            return []

        # 2. Prepare data
        ids = []
        vectors = []

        for m in memories_data:
            if m.get('embedding'):
                ids.append(str(m['id']).replace('memory:', ''))
                vectors.append(m['embedding'])

        if not vectors:
            return []

        X = np.array(vectors)

        # 3. Run K-Means
        kmeans = NumpyKMeans(n_clusters=min(n_clusters, len(X)))
        kmeans.fit(X)
        labels = kmeans.predict(X)

        # 4. Create Centroids
        centroids = []
        cluster_map = {} # cluster_index -> uuid

        for i, center in enumerate(kmeans.centroids):
            cluster_id = str(uuid.uuid4())
            cluster_map[i] = cluster_id

            # Calculate stats
            cluster_indices = np.where(labels == i)[0]
            member_count = len(cluster_indices)

            if member_count == 0:
                continue

            # Calculate radius (max distance)
            cluster_points = X[cluster_indices]
            distances = np.linalg.norm(cluster_points - center, axis=1)
            radius = float(np.max(distances)) if len(distances) > 0 else 0.0

            centroid = VectorCentroid(
                embedding=EmbeddingVector.from_numpy(center),
                cluster_id=cluster_id,
                member_count=member_count,
                radius=radius,
                metadata={"algorithm": "kmeans", "user_id": user_id}
            )

            # Save centroid
            await self.db_client.save_centroid(centroid)
            centroids.append(centroid)

        # 5. Update Memories
        for idx, label in enumerate(labels):
            memory_id = ids[idx]
            cluster_id = cluster_map[label]
            await self.db_client.update_memory_cluster(memory_id, cluster_id)

        logger.info(f"Clustering complete. Created {len(centroids)} centroids.")
        return centroids
