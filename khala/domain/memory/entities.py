"""Core domain entities for the memory system.

These entities represent the core business concepts and contain
business logic for memory management, following DDD principles.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
import uuid
from enum import Enum
import logging

from .value_objects import (
    EmbeddingVector, 
    ImportanceScore, 
    DecayScore, 
    MemoryTier,
    MemorySource,
    Sentiment,
    Location
)

logger = logging.getLogger(__name__)

@dataclass
class Memory:
    """Core memory entity representing a stored memory item."""
    
    # Business Rules Constants
    PROMOTION_WORKING_AGE_HOURS = 0.5
    PROMOTION_WORKING_ACCESS_COUNT = 5
    PROMOTION_WORKING_IMPORTANCE = 0.8
    PROMOTION_SHORT_TERM_DAYS = 15
    PROMOTION_SHORT_TERM_IMPORTANCE = 0.9
    ARCHIVE_AGE_DAYS = 90
    ARCHIVE_IMPORTANCE = 0.3

    # Core attributes
    user_id: str
    content: str
    tier: MemoryTier
    importance: ImportanceScore
    
    # Optional attributes with defaults
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    embedding: Optional[EmbeddingVector] = field(default=None)
    # Strategy 78: Multi-Vector
    embedding_visual: Optional[EmbeddingVector] = field(default=None)
    embedding_code: Optional[EmbeddingVector] = field(default=None)
    tags: List[str] = field(default_factory=list)
    category: Optional[str] = field(default=None)
    scope: Optional[str] = field(default=None)  # Strategy 148: Scoped Memories
    summary: Optional[str] = field(default=None)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Timestamps
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    # Usage tracking
    access_count: int = 0
    llm_cost: float = 0.0
    verification_score: float = 0.0
    verification_count: int = 0
    verification_status: str = "pending"
    verified_at: Optional[datetime] = None
    verification_issues: List[str] = field(default_factory=list)
    debate_consensus: Optional[Dict[str, Any]] = field(default=None)
    is_archived: bool = False
    decay_score: Optional[DecayScore] = field(default=None)
    
    # Tier 6: Advanced Metadata
    source: Optional[MemorySource] = field(default=None)  # Task 28: Traceability
    sentiment: Optional[Sentiment] = field(default=None)  # Task 37: Emotion
    
    # Module 12: Experimental
    episode_id: Optional[str] = None
    confidence: float = 1.0  # Strategy 135: Metacognitive Indexing
    source_reliability: float = 1.0  # Strategy 136: Source Reliability Scoring
    # Module 15: Version Control
    branch_id: Optional[str] = field(default=None)
    fork_parent_id: Optional[str] = field(default=None)
    # Module 11: Optimization Fields
    versions: List[Dict[str, Any]] = field(default_factory=list)
    events: List[Dict[str, Any]] = field(default_factory=list)
    location: Optional[Location] = field(default=None)

    # Phase 6: Advanced Research (Titans/MIRAS)
    surprise_score: float = 0.0
    surprise_momentum: float = 0.0
    retention_weight: float = 1.0

    @property
    def importance_score(self) -> ImportanceScore:
        """Alias for importance to support legacy code."""
        return self.importance

    def __hash__(self) -> int:
        """Hash based on ID."""
        return hash(self.id)

    def __eq__(self, other: object) -> bool:
        """Equality based on ID."""
        if not isinstance(other, Memory):
            return NotImplemented
        return self.id == other.id

    def __post_init__(self) -> None:
        """Validate memory entity with Self-Healing."""
        if not self.content.strip():
            # We allow empty content for "deleted" memories if needed, but warn
            logger.warning(f"Memory {self.id} has empty content.")
        
        if not self.user_id.strip():
            logger.warning(f"Memory {self.id} has empty user_id.")
        
        if self.access_count < 0:
            logger.warning(f"Memory {self.id} has negative access_count. Resetting to 0.")
            self.access_count = 0
        
        if self.llm_cost < 0:
            logger.warning(f"Memory {self.id} has negative llm_cost. Resetting to 0.")
            self.llm_cost = 0.0
    
    def should_promote_to_next_tier(self) -> bool:
        """Check if memory should be promoted to the next tier."""
        next_tier: Optional[MemoryTier] = self.tier.next_tier()
        if not next_tier:
            return False
        
        age_hours: float = self._get_age_hours()
        
        if self.tier == MemoryTier.WORKING:
            return (
                age_hours > self.PROMOTION_WORKING_AGE_HOURS and
                self.access_count > self.PROMOTION_WORKING_ACCESS_COUNT and
                self.importance.value > self.PROMOTION_WORKING_IMPORTANCE
            )
        elif self.tier == MemoryTier.SHORT_TERM:
            # FIX: Only promote if importance is high. Age alone causes archival, not promotion.
            return (
                self.importance.value > self.PROMOTION_SHORT_TERM_IMPORTANCE
            )
        
        return False
    
    def should_archive(self) -> bool:
        """Check if memory should be archived."""
        age_hours: float = self._get_age_hours()
        
        return (
            age_hours > self.ARCHIVE_AGE_DAYS * 24 and
            self.access_count == 0 and
            self.importance.value < self.ARCHIVE_IMPORTANCE
        )
    
    def promote(self) -> None:
        """Promote memory to the next tier."""
        next_tier: Optional[MemoryTier] = self.tier.next_tier()
        if not next_tier:
            raise ValueError(f"Cannot promote from {self.tier.value} tier")
        
        if not self.should_promote_to_next_tier():
            raise ValueError(f"Memory does not meet promotion criteria")
        
        self.tier = next_tier
        self.updated_at = datetime.now(timezone.utc)
    
    def archive(self, force: bool = False) -> None:
        """Archive this memory."""
        if not force and not self.should_archive():
            raise ValueError("Memory does not meet archival criteria")
        
        self.is_archived = True
        self.updated_at = datetime.now(timezone.utc)
    
    def record_access(self) -> None:
        """Record that this memory was accessed."""
        self.access_count += 1
        self.accessed_at = datetime.now(timezone.utc)
    
    def calculate_decay_score(self, half_life_days: int = 30) -> DecayScore:
        """Calculate decay score based on age and importance."""
        age_days: float = self.get_age_hours() / 24.0
        self.decay_score = DecayScore.calculate(
            self.importance, age_days, half_life_days
        )
        return self.decay_score
    
    def update_verification_score(
        self, 
        score: float, 
        issues: Optional[List[str]] = None
    ) -> None:
        """Update verification score and issues."""
        if not (0.0 <= score <= 1.0):
            raise ValueError("Verification score must be in [0.0, 1.0]")
        
        self.verification_score = score
        if issues:
            self.verification_issues = issues
        else:
            self.verification_issues = []
        
        self.updated_at = datetime.now(timezone.utc)
    
    def add_keyword_tag(self, keyword: str) -> None:
        """Add a tag to this memory."""
        if keyword and keyword.strip() not in self.tags:
            self.tags.append(keyword.strip())
            self.updated_at = datetime.now(timezone.utc)
    
    def _get_age_hours(self) -> float:
        """Get age of memory in hours."""
        now: datetime = datetime.now(timezone.utc)
        age: timedelta = now - self.created_at
        return age.total_seconds() / 3600.0

    def get_age_hours(self) -> float:
        """Public helper for consumers requiring age calculations."""
        return self._get_age_hours()


class EntityType(Enum):
    """Types of entities that can be extracted from memories."""
    
    PERSON = "person"
    TOOL = "tool"
    CONCEPT = "concept"
    PLACE = "place"
    EVENT = "event"
    ORGANIZATION = "organization"
    DATE = "date"
    NUMBER = "number"


@dataclass
class Entity:
    """Entity extracted from memory content."""
    
    text: str
    entity_type: EntityType
    confidence: float
    embedding: Optional[EmbeddingVector] = field(default=None)
    metadata: Dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def __post_init__(self) -> None:
        """Validate entity after creation."""
        if not self.text.strip():
            logger.warning(f"Entity {self.id} has empty text.")
        
        if not (0.0 <= self.confidence <= 1.0):
            logger.warning(f"Entity {self.id} confidence {self.confidence} out of range. Clamping.")
            self.confidence = max(0.0, min(1.0, self.confidence))
    
    def is_high_confidence(self, threshold: float = 0.8) -> bool:
        """Check if entity has high confidence."""
        return self.confidence >= threshold


@dataclass
class Relationship:
    """Relationship between two entities."""
    
    from_entity_id: str
    to_entity_id: str
    relation_type: str
    strength: float
    weight: float = 1.0  # Strategy 68: Weighted Directed Multigraph
    valid_from: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    valid_to: Optional[datetime] = field(default=None)
    transaction_time_start: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    transaction_time_end: Optional[datetime] = field(default=None)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    
    def __post_init__(self) -> None:
        """Validate relationship after creation."""
        if not self.relation_type.strip():
            logger.warning(f"Relationship {self.id} has empty relation_type.")
        
        if not (0.0 <= self.strength <= 1.0):
            logger.warning(f"Relationship {self.id} strength {self.strength} out of range. Clamping.")
            self.strength = max(0.0, min(1.0, self.strength))
        
        if self.valid_to and self.valid_to <= self.valid_from:
            logger.warning(f"Relationship {self.id} valid_to <= valid_from.")

        if self.transaction_time_end and self.transaction_time_end <= self.transaction_time_start:
            logger.warning(f"Relationship {self.id} transaction_time_end <= transaction_time_start.")
    
    def is_active(self) -> bool:
        """Check if relationship is currently active."""
        now: datetime = datetime.now(timezone.utc)
        return now >= self.valid_from and (
            self.valid_to is None or now <= self.valid_to
        )
    
    def expire(self) -> None:
        """Mark relationship as expired."""
        self.valid_to = datetime.now(timezone.utc)
