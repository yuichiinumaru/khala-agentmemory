import pytest
import numpy as np
from unittest.mock import AsyncMock, MagicMock, patch
from khala.application.services.vector_ops import AdvancedVectorService
from khala.infrastructure.surrealdb.client import SurrealDBClient

@pytest.fixture
def mock_db_client():
    client = MagicMock(spec=SurrealDBClient)
    client.get_connection.return_value.__aenter__.return_value = AsyncMock()
    client.get_connection.return_value.__aexit__.return_value = None
    return client

@pytest.fixture
def vector_service(mock_db_client):
    return AdvancedVectorService(mock_db_client)

def test_quantize_vector(vector_service):
    """Test Strategy 79: Quantization"""
    vec = [0.1, -0.5, 0.9, 0.0]
    quantized = vector_service.quantize_vector(vec, method="int8")

    assert len(quantized) == 4
    assert isinstance(quantized[0], int)
    # 0.1 * 127 = 12.7 -> 12
    # -0.5 * 127 = -63.5 -> -63
    # 0.9 * 127 = 114.3 -> 114
    assert quantized[0] == 12
    assert quantized[1] == -63
    assert quantized[2] == 114
    assert quantized[3] == 0

def test_dequantize_vector(vector_service):
    """Test Strategy 79: De-quantization"""
    q_vec = [12, -63, 114, 0]
    vec = vector_service.dequantize_vector(q_vec, method="int8")

    assert len(vec) == 4
    assert abs(vec[0] - 0.094) < 0.01  # 12/127 ~= 0.094
    assert abs(vec[1] - (-0.496)) < 0.01
    assert abs(vec[2] - 0.897) < 0.01

def test_reduce_dimensions(vector_service):
    """Test Strategy 82: Adaptive Dimensions"""
    vec = [0.5, 0.5, 0.5, 0.5] # norm = 1.0
    reduced = vector_service.reduce_dimensions(vec, target_dim=2)

    assert len(reduced) == 2
    # Should be normalized
    norm = np.linalg.norm(reduced)
    assert abs(norm - 1.0) < 0.0001
    assert reduced[0] == reduced[1]

def test_interpolate_vectors(vector_service):
    """Test Strategy 84: Interpolation"""
    v1 = [1.0, 0.0]
    v2 = [0.0, 1.0]

    # Midpoint
    mid = vector_service.interpolate_vectors(v1, v2, alpha=0.5)

    assert abs(mid[0] - mid[1]) < 0.0001
    # Normalized: (0.5, 0.5) -> normalized is (0.707, 0.707)
    assert abs(mid[0] - 0.7071) < 0.001

@pytest.mark.asyncio
async def test_compute_clusters(vector_service, mock_db_client):
    """Test Strategy 81: Clustering"""
    # Mock data: 4 points, 2 clusters (roughly)
    # Cluster 1: near [1, 0]
    # Cluster 2: near [0, 1]
    memories = [
        {"id": "mem:1", "embedding": [0.9, 0.1]},
        {"id": "mem:2", "embedding": [0.8, 0.2]},
        {"id": "mem:3", "embedding": [0.1, 0.9]},
        {"id": "mem:4", "embedding": [0.2, 0.8]},
    ]

    conn = mock_db_client.get_connection.return_value.__aenter__.return_value
    conn.query.return_value = memories
    # create returns a list of created records usually, or a single record dict
    # adjusting side_effect to return list of single record as per SurrealDBClient.create behavior which might return a list
    # But checking the code, code expects created[0]["id"]
    conn.create.side_effect = [[{"id": "cluster:1"}], [{"id": "cluster:2"}]]

    result = await vector_service.compute_clusters(k=2, sample_size=10)

    assert result["status"] == "success"
    assert result["clusters_created"] == 2
    assert result["memories_updated"] == 4

    # Check calls
    assert conn.create.call_count == 2
    assert conn.query.call_count >= 2 # Select + Delete + Updates

@pytest.mark.asyncio
async def test_detect_drift(vector_service, mock_db_client):
    """Test Strategy 80: Drift Detection"""
    vectors = [{"embedding": [1.0, 0.0]}, {"embedding": [0.9, 0.1]}]
    conn = mock_db_client.get_connection.return_value.__aenter__.return_value

    # First call returns memories, second call returns NO previous stats
    conn.query.side_effect = [vectors, []]

    result = await vector_service.detect_drift()

    assert result["sample_count"] == 2
    assert result["drift_score"] == 0.0 # No previous history

    # Test with history
    conn.query.side_effect = [
        vectors,
        [{"mean_embedding": [0.0, 1.0]}] # Previous mean far away
    ]

    result = await vector_service.detect_drift()

    # Current mean is approx [0.95, 0.05]
    # Prev mean [0.0, 1.0]
    # Distance should be high
    assert result["drift_score"] > 0.8

@pytest.mark.asyncio
async def test_detect_anomalies(vector_service, mock_db_client):
    """Test Strategy 83: Anomaly Detection"""
    # 3 normal points, 1 outlier
    data = [
        {"id": "1", "embedding": [1.0, 0.0], "cluster_id": "c1", "centroid": [1.0, 0.0], "radius": 0.5},
        {"id": "2", "embedding": [0.9, 0.1], "cluster_id": "c1", "centroid": [1.0, 0.0], "radius": 0.5},
        {"id": "3", "embedding": [0.95, 0.05], "cluster_id": "c1", "centroid": [1.0, 0.0], "radius": 0.5},
        {"id": "4", "embedding": [0.0, 1.0], "cluster_id": "c1", "centroid": [1.0, 0.0], "radius": 0.5}, # Outlier
    ]

    conn = mock_db_client.get_connection.return_value.__aenter__.return_value
    conn.query.return_value = data

    anomalies = await vector_service.detect_anomalies(threshold_std=1.5)

    assert len(anomalies) == 1
    assert anomalies[0]["id"] == "4"
