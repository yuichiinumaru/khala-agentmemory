"""Monitoring domain entities."""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, Any, Optional
import uuid

@dataclass
class GraphSnapshot:
    """Snapshot of graph metrics at a point in time."""

    node_count: int
    edge_count: int
    avg_degree: float
    density: float
    metadata: Dict[str, Any] = field(default_factory=dict)

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "node_count": self.node_count,
            "edge_count": self.edge_count,
            "avg_degree": self.avg_degree,
            "density": self.density,
            "metadata": self.metadata
        }

@dataclass
class SystemMetric:
    """System metric recording."""

    metric_name: str
    value: float
    labels: Dict[str, str] = field(default_factory=dict)

    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "metric_name": self.metric_name,
            "value": self.value,
            "labels": self.labels
        }
