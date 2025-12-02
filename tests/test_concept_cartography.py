import pytest
import numpy as np
from datetime import datetime
from unittest.mock import MagicMock
from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.value_objects import EmbeddingVector
from khala.application.services.concept_cartography_service import ConceptCartographyService

def create_mock_memory(id, values):
    return Memory(
        id=id,
        user_id="test_user",
        content="test content",
        tier=MemoryTier.WORKING,
        importance=ImportanceScore(0.5),
        embedding=EmbeddingVector(values)
    )

def test_concept_cartography_empty():
    service = ConceptCartographyService()
    result = service.project_memories([])
    assert result == {}

def test_concept_cartography_single():
    service = ConceptCartographyService()
    mem1 = create_mock_memory("1", [0.1, 0.2, 0.3])
    result = service.project_memories([mem1])
    assert result["1"]["x"] == 0.0
    assert result["1"]["y"] == 0.0

def test_concept_cartography_multiple():
    service = ConceptCartographyService()
    # Create 3 points in 3D space
    mem1 = create_mock_memory("1", [1.0, 0.0, 0.0])
    mem2 = create_mock_memory("2", [0.0, 1.0, 0.0])
    mem3 = create_mock_memory("3", [0.0, 0.0, 1.0])

    result = service.project_memories([mem1, mem2, mem3])

    assert len(result) == 3
    for mid in ["1", "2", "3"]:
        assert mid in result
        assert "x" in result[mid]
        assert "y" in result[mid]
        assert isinstance(result[mid]["x"], float)
        assert isinstance(result[mid]["y"], float)

    # Check distinctiveness (points should not all be 0,0 if they are different)
    # PCA centers data, so sum should be close to 0
    xs = [result[mid]["x"] for mid in result]
    ys = [result[mid]["y"] for mid in result]

    assert np.std(xs) > 0.001
    assert np.std(ys) > 0.001

def test_concept_cartography_error_handling():
    service = ConceptCartographyService()
    mem1 = create_mock_memory("1", [0.1, 0.2])

    # Mock np.linalg.svd to raise exception
    original_svd = np.linalg.svd
    np.linalg.svd = MagicMock(side_effect=Exception("SVD failed"))

    result = service.project_memories([mem1, mem1]) # duplicates to allow PCA attempt

    assert result["1"]["x"] == 0.0
    assert result["1"]["y"] == 0.0

    np.linalg.svd = original_svd
