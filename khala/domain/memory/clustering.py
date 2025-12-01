"""Domain entities for vector clustering.

These entities represent the clustering concepts in the memory system,
including vector centroids for fast search and organization.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid

from .value_objects import EmbeddingVector


@dataclass
class VectorCentroid:
    """Represents a centroid in the vector space."""

    embedding: EmbeddingVector
    cluster_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    member_count: int = 0
    radius: float = 0.0  # Max distance from centroid to any member
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        """Validate centroid entity."""
        if self.member_count < 0:
            raise ValueError("Member count cannot be negative")
        if self.radius < 0:
            raise ValueError("Radius cannot be negative")
