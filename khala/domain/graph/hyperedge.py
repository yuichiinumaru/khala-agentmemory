from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import uuid
from datetime import datetime, timezone

from khala.domain.memory.entities import Entity, EntityType
from khala.domain.memory.value_objects import EmbeddingVector

@dataclass
class Hyperedge(Entity):
    """
    Represents an N-ary relationship as a hypernode.
    Strategy 66: Hyperedge Emulation.
    Strategy 42: Hyperedges.
    """
    participants: List[str] = field(default_factory=list) # List of Entity IDs
    hyperedge_type: str = "generic"

    def __post_init__(self):
        # Override entity attributes for Hyperedge specifics if needed
        # We enforce EVENT type for hyperedges typically, or CONCEPT
        if self.entity_type != EntityType.EVENT:
             # Just a soft enforcement or we leave it flexible
             pass

        if not self.metadata:
            self.metadata = {}

        self.metadata.update({
            "is_hyperedge": True,
            "hyperedge_type": self.hyperedge_type,
            "participant_count": len(self.participants),
            "participant_ids": self.participants
        })

        super().__post_init__()

    @classmethod
    def create(cls,
               text: str,
               participants: List[str],
               hyperedge_type: str,
               confidence: float = 1.0,
               metadata: Dict[str, Any] = None) -> 'Hyperedge':
        """Factory method to create a new Hyperedge."""
        return cls(
            text=text,
            entity_type=EntityType.EVENT,
            confidence=confidence,
            participants=participants,
            hyperedge_type=hyperedge_type,
            metadata=metadata or {}
        )

    @classmethod
    def from_entity(cls, entity: Entity) -> Optional['Hyperedge']:
        """Reconstruct Hyperedge from Entity if applicable."""
        if not entity.metadata or not entity.metadata.get("is_hyperedge"):
            return None

        participants = entity.metadata.get("participant_ids", [])
        hyperedge_type = entity.metadata.get("hyperedge_type", "generic")

        return cls(
            text=entity.text,
            entity_type=entity.entity_type,
            confidence=entity.confidence,
            embedding=entity.embedding,
            metadata=entity.metadata,
            id=entity.id,
            created_at=entity.created_at,
            participants=participants,
            hyperedge_type=hyperedge_type
        )
