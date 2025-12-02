"""Unit tests for memory domain value objects.

Following TDD principles, these tests verify the business logic
and constraints of value objects in the memory domain.
"""

import pytest
import numpy as np
from datetime import datetime, timezone, timedelta

from khala.domain.memory.value_objects import (
    EmbeddingVector,
    ImportanceScore,
    DecayScore,
    MemoryTier,
)


class TestEmbeddingVector:
    """Test cases for EmbeddingVector value object."""
    
    def test_valid_embedding_creation(self):
        """Test creating a valid embedding vector."""
        values = [0.1, -0.2, 0.3] + [0.0] * 765  # 768 dimensions
        embedding = EmbeddingVector(values)
        
        assert embedding.dimensions == 768
        assert len(embedding.values) == 768
        assert embedding.to_numpy().shape == (768,)
    
    def test_embedding_wrong_dimensions(self):
        """Test embedding with wrong number of dimensions."""
        values = [0.1, 0.2, 0.3]  # Only 3 dimensions
        
        with pytest.raises(ValueError, match="Embedding must have 768 dimensions"):
            EmbeddingVector(values)
    
    def test_embedding_invalid_values(self):
        """Test embedding with invalid values."""
        # Test value out of range
        values = [1.5] + [0.0] * 767  # 1.5 is beyond [-1, 1] range
        with pytest.raises(ValueError, match="Embedding values must be floats"):
            EmbeddingVector(values)
        
        # Test non-float value
        values = ["invalid"] + [0.0] * 767
        with pytest.raises(ValueError, match="Embedding values must be floats"):
            EmbeddingVector(values)
    
    def test_embedding_from_numpy(self):
        """Test creating embedding from numpy array."""
        array = np.random.uniform(-1, 1, 768).astype(np.float32)
        embedding = EmbeddingVector.from_numpy(array)
        
        assert len(embedding.values) == 768
        np.testing.assert_array_almost_equal(
            embedding.to_numpy(), array, decimal=6
        )


class TestImportanceScore:
    """Test cases for ImportanceScore value object."""
    
    def test_valid_importance_creation(self):
        """Test creating valid importance scores."""
        scores = [0.0, 0.25, 0.5, 0.75, 1.0]
        
        for score in scores:
            importance = ImportanceScore(score)
            assert importance.value == score
    
    def test_importance_out_of_range(self):
        """Test importance scores outside valid range."""
        # Test negative
        with pytest.raises(ValueError, match="Importance score must be in"):
            ImportanceScore(-0.1)
        
        # Test > 1.0
        with pytest.raises(ValueError, match="Importance score must be in"):
            ImportanceScore(1.1)
    
    def test_importance_non_numeric(self):
        """Test non-numeric importance score."""
        with pytest.raises(TypeError, match="Importance score must be a number"):
            ImportanceScore("high")
    
    def test_importance_factory_methods(self):
        """Test factory method constructors."""
        very_high = ImportanceScore.very_high()
        assert very_high.value == 0.9
        
        high = ImportanceScore.high()
        assert high.value == 0.75
        
        medium = ImportanceScore.medium()
        assert medium.value == 0.5
        
        low = ImportanceScore.low()
        assert low.value == 0.25
        
        very_low = ImportanceScore.very_low()
        assert very_low.value == 0.1


class TestDecayScore:
    """Test cases for DecayScore value object."""
    
    def test_decay_score_calculation(self):
        """Test calculating decay score."""
        importance = ImportanceScore(0.8)
        decay = DecayScore.calculate(importance, age_days=30, half_life_days=30)
        
        # After one half-life, score should be ~0.4
        expected = importance.value * 0.368  # exp(-1) ≈ 0.368
        assert abs(decay.value - expected) < 0.01
    
    def test_decay_score_immediate(self):
        """Test decay score for new memory."""
        importance = ImportanceScore(0.9)
        decay = DecayScore.calculate(importance, age_days=0)
        
        # New memory should have score very close to original
        assert abs(decay.value - importance.value) < 0.01
    
    def test_decay_score_old_memory(self):
        """Test decay score for old memory."""
        importance = ImportanceScore(0.9)
        decay = DecayScore.calculate(importance, age_days=90, half_life_days=30)
        
        # After 3 half-lives, score should be ~11% of original
        expected = importance.value * 0.049  # exp(-3) ≈ 0.049
        assert abs(decay.value - expected) < 0.01
    
    def test_decay_score_negative_half_life(self):
        """Test decay score with negative half-life."""
        importance = ImportanceScore(0.8)
        
        with pytest.raises(ValueError, match="Half-life must be positive"):
            DecayScore.calculate(importance, age_days=10, half_life_days=-30)


class TestMemoryTier:
    """Test cases for MemoryTier enum."""
    
    def test_tier_ttl_hours(self):
        """Test TTL hours for each tier."""
        assert MemoryTier.WORKING.ttl_hours() == 1
        assert MemoryTier.SHORT_TERM.ttl_hours() == 360  # 15 days * 24 hours
        assert MemoryTier.LONG_TERM.ttl_hours() == -1  # Persistent
    
    def test_tier_promotion_path(self):
        """Test promotion path between tiers."""
        assert MemoryTier.WORKING.next_tier() == MemoryTier.SHORT_TERM
        assert MemoryTier.SHORT_TERM.next_tier() == MemoryTier.LONG_TERM
        assert MemoryTier.LONG_TERM.next_tier() is None
