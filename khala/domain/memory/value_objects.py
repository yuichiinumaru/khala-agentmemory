"""Value objects for the memory domain.

Immutable value objects that represent concepts in the memory system.
Following DDD principles, these objects have no identity and are
defined by their values.
"""

from dataclasses import dataclass, field
from typing import List, Final, Optional, Dict
from datetime import datetime
from enum import Enum
import numpy as np


@dataclass(frozen=True)
class EmbeddingVector:
    """Immutable embedding vector for semantic search."""
    
    values: List[float]
    dimensions: int = 768  # Gemini embedding dimension
    
    def __post_init__(self) -> None:
        """Validate the embedding vector."""
        if len(self.values) != self.dimensions:
            raise ValueError(
                f"Embedding must have {self.dimensions} dimensions, "
                f"got {len(self.values)}"
            )
        
        # Check if all values are valid floats
        for value in self.values:
            if not isinstance(value, (float, int)) or not (-1 <= value <= 1):
                raise ValueError(
                    f"Embedding values must be floats in [-1, 1], got {value}"
                )
    
    def to_numpy(self) -> np.ndarray:
        """Convert to numpy array for computations."""
        return np.array(self.values, dtype=np.float32)
    
    @classmethod
    def from_numpy(cls, array: np.ndarray) -> "EmbeddingVector":
        """Create from numpy array."""
        return cls(values=array.tolist())


@dataclass(frozen=True)
class ImportanceScore:
    """Immutable importance score for memory ranking."""
    
    value: float
    
    def __post_init__(self) -> None:
        """Validate importance score."""
        if not isinstance(self.value, (float, int)):
            raise TypeError("Importance score must be a number")
        if not (0.0 <= self.value <= 1.0):
            raise ValueError("Importance score must be in [0.0, 1.0]")
    
    @classmethod
    def very_high(cls) -> "ImportanceScore":
        """Create very high importance score."""
        return cls(0.9)
    
    @classmethod 
    def high(cls) -> "ImportanceScore":
        """Create high importance score."""
        return cls(0.75)
    
    @classmethod
    def medium(cls) -> "ImportanceScore":
        """Create medium importance score."""
        return cls(0.5)
    
    @classmethod
    def low(cls) -> "ImportanceScore":
        """Create low importance score."""
        return cls(0.25)
    
    @classmethod
    def very_low(cls) -> "ImportanceScore":
        """Create very low importance score."""
        return cls(0.1)


@dataclass(frozen=True)
class DecayScore:
    """Immutable decay score for memory aging."""
    
    value: float
    half_life_days: int = 30  # Default half-life of 30 days
    
    def __post_init__(self) -> None:
        """Validate decay score."""
        if not isinstance(self.value, (float, int)):
            raise TypeError("Decay score must be a number")
        if not (0.0 <= self.value <= 1.0):
            raise ValueError("Decay score must be in [0.0, 1.0]")
        if self.half_life_days <= 0:
            raise ValueError("Half-life must be positive")
    
    @classmethod
    def calculate(
        cls, 
        original_importance: ImportanceScore, 
        age_days: float, 
        half_life_days: int = 30
    ) -> "DecayScore":
        """Calculate decay score using exponential decay formula.
        
        Formula: score = importance * exp(-age_days / half_life_days)
        
        Args:
            original_importance: Original importance before decay
            age_days: Age in days
            half_life_days: Half-life in days
            
        Returns:
            Calculated decay score
        """
        import math
        decayed = original_importance.value * math.exp(-age_days / half_life_days)
        return cls(value=min(decayed, 1.0), half_life_days=half_life_days)


class MemoryTier(Enum):
    """Memory tier enum for lifecycle management."""
    
    WORKING = "working"      # 1 hour TTL, active processing
    SHORT_TERM = "short_term"  # 15 days TTL, recent memories
    LONG_TERM = "long_term"   # Persistent, important memories
    
    def ttl_hours(self) -> int:
        """Get TTL in hours for this tier."""
        ttl_map = {
            MemoryTier.WORKING: 1,
            MemoryTier.SHORT_TERM: 15 * 24,  # 15 days
            MemoryTier.LONG_TERM: -1,  # Persistent
        }
        return ttl_map[self]
    
    def next_tier(self) -> "MemoryTier | None":
        """Get the next tier in the promotion path."""
        promotion_map = {
            MemoryTier.WORKING: MemoryTier.SHORT_TERM,
            MemoryTier.SHORT_TERM: MemoryTier.LONG_TERM,
            MemoryTier.LONG_TERM: None,  # No promotion from long-term
        }
        return promotion_map[self]


@dataclass(frozen=True)
class MemorySource:
    """Immutable source information for memory traceability (Task 28)."""
    
    source_type: str  # e.g., "user_input", "document", "web", "system", "inference"
    source_id: Optional[str] = None  # ID of the source (e.g., message ID, file path)
    location: Optional[str] = None  # Specific location (e.g., line number, URL)
    timestamp: Optional[datetime] = None  # When the source was created/accessed
    confidence: float = 1.0  # Confidence in this source (0.0-1.0)
    
    def __post_init__(self) -> None:
        """Validate memory source."""
        if not self.source_type.strip():
            raise ValueError("Source type cannot be empty")
        if not (0.0 <= self.confidence <= 1.0):
            raise ValueError("Confidence must be in [0.0, 1.0]")


@dataclass(frozen=True)
class Sentiment:
    """Immutable sentiment analysis for emotion-driven memory (Task 37)."""
    
    score: float  # -1.0 (negative) to 1.0 (positive)
    label: str  # e.g., "positive", "negative", "neutral", "joy", "anger"
    emotions: Dict[str, float] = field(default_factory=dict)  # Detailed emotions e.g. {"joy": 0.8}
    
    def __post_init__(self) -> None:
        """Validate sentiment."""
        if not (-1.0 <= self.score <= 1.0):
            raise ValueError("Sentiment score must be in [-1.0, 1.0]")
        if not self.label.strip():
            raise ValueError("Sentiment label cannot be empty")

