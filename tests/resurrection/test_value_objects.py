import pytest
import numpy as np
from khala.domain.memory.value_objects import EmbeddingVector

def test_embedding_vector_tolerance():
    # Test case slightly above 1.0 (e.g. 1.00005)
    # With tolerance 1e-4, 1.00005 is valid ( <= 1.0001)
    vec = EmbeddingVector(values=[1.00005, -0.99999, 0.0])
    assert vec.values[0] > 1.0

    # Test case significantly above 1.0 (should fail)
    with pytest.raises(ValueError):
        EmbeddingVector(values=[1.1, 0.0])

    # Test numpy conversion
    arr = vec.to_numpy()
    assert isinstance(arr, np.ndarray)
    assert arr.dtype == np.float32
