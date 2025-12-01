"""Verification script for clustering and adaptive vector dimensions."""

import asyncio
import uuid
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock
import numpy as np

from khala.domain.memory.entities import Memory, MemoryTier
from khala.domain.memory.value_objects import ImportanceScore, EmbeddingVector
from khala.domain.memory.clustering import VectorCentroid
from khala.domain.memory.services import MemoryService
from khala.domain.memory.clustering_service import VectorClusteringService, NumpyKMeans
from khala.infrastructure.surrealdb.client import SurrealDBClient

async def verify_adaptive_vector():
    print("Verifying Adaptive Vector Dimensions...")
    service = MemoryService()

    # Create a memory with low importance and full embedding (dim=10)
    # Using small dimension for test simplicity, but logic checks > 256
    # Let's mock a larger vector
    full_embedding = [0.1] * 768

    memory = Memory(
        user_id="test_user",
        content="Test content",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.2), # Low importance
        embedding=EmbeddingVector(full_embedding)
    )

    # Run adaptation
    service.adapt_vector_dimensions(memory)

    if memory.embedding_small:
        print(f"SUCCESS: Small embedding created with dimension {len(memory.embedding_small.values)}")
        assert len(memory.embedding_small.values) == 256
    else:
        print("FAILURE: Small embedding not created")

async def verify_clustering():
    print("\nVerifying Vector Clustering...")

    # Mock DB Client
    db_client = AsyncMock(spec=SurrealDBClient)
    db_client.get_connection = MagicMock()

    # Mock context manager for get_connection
    conn_mock = AsyncMock()
    # Return list of results (list of dicts)
    conn_mock.query.return_value = [[
        {"id": "memory:1", "embedding": [1.0, 0.0, 0.0]},
        {"id": "memory:2", "embedding": [0.9, 0.1, 0.0]},
        {"id": "memory:3", "embedding": [0.0, 1.0, 0.0]},
        {"id": "memory:4", "embedding": [0.1, 0.9, 0.0]}
    ]]

    db_client.get_connection.return_value.__aenter__.return_value = conn_mock

    service = VectorClusteringService(db_client)

    # Run clustering (2 clusters expected)
    centroids = await service.perform_clustering("test_user", n_clusters=2)

    print(f"Created {len(centroids)} centroids")
    for c in centroids:
        print(f"Centroid: members={c.member_count}, radius={c.radius}")

    assert len(centroids) == 2
    assert db_client.save_centroid.call_count == 2
    assert db_client.update_memory_cluster.call_count == 4
    print("SUCCESS: Clustering logic verified")

def verify_kmeans():
    print("\nVerifying Numpy K-Means...")
    X = np.array([
        [1.0, 0.0], [0.9, 0.1], # Cluster 1
        [0.0, 1.0], [0.1, 0.9]  # Cluster 2
    ])

    kmeans = NumpyKMeans(n_clusters=2)
    kmeans.fit(X)
    labels = kmeans.predict(X)

    print(f"Labels: {labels}")
    # Should group 0,1 together and 2,3 together
    assert labels[0] == labels[1]
    assert labels[2] == labels[3]
    assert labels[0] != labels[2]
    print("SUCCESS: K-Means logic verified")

async def main():
    await verify_adaptive_vector()
    verify_kmeans()
    await verify_clustering()

if __name__ == "__main__":
    asyncio.run(main())
