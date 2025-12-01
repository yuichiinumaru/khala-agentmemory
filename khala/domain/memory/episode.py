"""Episode entity for the memory system.

Episodes are discrete units of experience that group related memories together,
enabling narrative threading and episodic retrieval.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional
import uuid
from enum import Enum


class EpisodeStatus(Enum):
    """Status of an episode."""
    OPEN = "open"       # Currently active episode
    CLOSED = "closed"   # Completed episode
    ARCHIVED = "archived" # Old episode, moved to deep storage


@dataclass
class Episode:
    """Episode entity representing a discrete unit of experience."""

    user_id: str
    title: str
    description: Optional[str] = None

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    status: EpisodeStatus = EpisodeStatus.OPEN

    # Timestamps
    started_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ended_at: Optional[datetime] = None

    # Metadata
    summary: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)

    # Links
    memory_ids: List[str] = field(default_factory=list) # IDs of memories in this episode
    parent_episode_id: Optional[str] = None # For hierarchical episodes

    def __post_init__(self) -> None:
        """Validate episode after creation."""
        if not self.title.strip():
            raise ValueError("Episode title cannot be empty")
        if not self.user_id.strip():
            raise ValueError("User ID cannot be empty")

    def close(self, summary: Optional[str] = None) -> None:
        """Close the episode."""
        self.status = EpisodeStatus.CLOSED
        self.ended_at = datetime.now(timezone.utc)
        if summary:
            self.summary = summary

    def add_memory(self, memory_id: str) -> None:
        """Add a memory ID to the episode."""
        if memory_id not in self.memory_ids:
            self.memory_ids.append(memory_id)

    @property
    def duration(self) -> Optional[float]:
        """Get duration in seconds if closed."""
        if self.ended_at:
            return (self.ended_at - self.started_at).total_seconds()
        return None
