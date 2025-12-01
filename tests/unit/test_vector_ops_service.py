import pytest
from unittest.mock import AsyncMock, MagicMock
import numpy as np
from khala.application.services.vector_ops_service import VectorOpsService
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector

@pytest.fixture
def mock_db_client():
    client = AsyncMock()
    return client

@pytest.fixture
def service(mock_db_client):
    return VectorOpsService(mock_db_client)

@pytest.mark.asyncio
async def test_interpolate_vectors(service, mock_db_client):
    # Setup
    user_id = "user1"
    mid1 = "mem1"
    mid2 = "mem2"

    vec1 = [0.1, 0.2, 0.3]
    vec2 = [0.3, 0.2, 0.1]

    mem1 = MagicMock(spec=Memory)
    mem1.embedding = EmbeddingVector(vec1)
    mem1.id = mid1

    mem2 = MagicMock(spec=Memory)
    mem2.embedding = EmbeddingVector(vec2)
    mem2.id = mid2

    mock_db_client.get_memory.side_effect = [mem1, mem2]

    mock_db_client.search_memories_by_vector.return_value = [
        {"id": "mem3", "content": "bridge"},
        {"id": "mem1", "content": "source1"}, # Should be filtered
    ]

    # Execute
    results = await service.interpolate_vectors(user_id, mid1, mid2, alpha=0.5)

    # Verify
    assert len(results) == 1
    assert results[0]["id"] == "mem3"

    # Check interpolation logic
    # Expected: 0.5*[0.1, 0.2, 0.3] + 0.5*[0.3, 0.2, 0.1] = [0.2, 0.2, 0.2]
    expected_vec = [0.2, 0.2, 0.2]

    call_args = mock_db_client.search_memories_by_vector.call_args
    assert call_args is not None
    embedding_arg = call_args.kwargs['embedding']
    assert np.allclose(embedding_arg.values, expected_vec)

@pytest.mark.asyncio
async def test_detect_anomalies(service, mock_db_client):
    # Setup
    user_id = "user1"

    # 3 sample memories
    vec1 = [1.0, 0.0]
    vec2 = [0.0, 1.0]
    vec3 = [1.0, 1.0] # Centroid should be [0.66, 0.66]

    mem1 = MagicMock(spec=Memory)
    mem1.embedding = EmbeddingVector(vec1)
    mem2 = MagicMock(spec=Memory)
    mem2.embedding = EmbeddingVector(vec2)
    mem3 = MagicMock(spec=Memory)
    mem3.embedding = EmbeddingVector(vec3)

    mock_db_client.get_latest_memories.return_value = [mem1, mem2, mem3]

    mock_db_client.find_outliers_by_centroid.return_value = [
        {"id": "outlier1", "similarity": 0.1}
    ]

    # Execute
    outliers = await service.detect_anomalies(user_id, sample_size=3)

    # Verify
    assert len(outliers) == 1
    assert outliers[0]["id"] == "outlier1"

    # Verify centroid calculation
    # Mean of (1,0), (0,1), (1,1) -> (2/3, 2/3) -> (0.66..., 0.66...)
    call_args = mock_db_client.find_outliers_by_centroid.call_args
    centroid_arg = call_args.kwargs['centroid']
    assert np.allclose(centroid_arg, [2/3, 2/3])
