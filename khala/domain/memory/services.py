"""Domain services for memory management.

These services contain business logic for managing memories,
entities, and relationships following DDD principles.
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any, Tuple
import asyncio
import hashlib

from .entities import Memory, Entity, Relationship, MemoryTier
from .value_objects import EmbeddingVector, ImportanceScore


class MemoryService:
    """Domain service for memory operations."""
    
    def calculate_promotion_score(self, memory: Memory) -> float:
        """Calculate promotion score for a memory.
        
        Returns a score from 0.0 to 1.0 indicating how likely
        the memory should be promoted to the next tier.
        """
        score = 0.0
        
        # Age score (older memories get higher scores)
        age_hours = memory._get_age_hours()
        if memory.tier.name == "WORKING" and age_hours > 0.5:
            score += 0.3
        elif memory.tier.name == "SHORT_TERM" and age_hours > 360:  # 15 days
            score += 0.4
        
        # Access count score
        if memory.access_count > 5:
            score += 0.3
        elif memory.access_count > 2:
            score += 0.2
        
        # Importance score
        score += memory.importance.value * 0.4
        
        return min(score, 1.0)
    
    def should_consolidate(self, memories: List[Memory]) -> bool:
        """Determine if memories should be consolidated."""
        # Simple heuristic: consolidate if we have >100 memories
        # in the same tier from the same user
        if not memories:
            return False

        user_memories = [m for m in memories if m.user_id == memories[0].user_id]
        tier_counts = {}
        for memory in user_memories:
            tier_counts[memory.tier] = tier_counts.get(memory.tier, 0) + 1
        
        return max(tier_counts.values(), default=0) > 100

    def adapt_vector_dimensions(self, memory: Memory) -> None:
        """Adapt vector dimensions based on importance (Strategy 82).

        If memory importance is low (< 0.3) and it has a full embedding,
        create a smaller, truncated embedding to save space/compute in
        secondary indexes.
        """
        if memory.importance.value < 0.3 and memory.embedding:
            # Create truncated embedding (first 256 dimensions)
            # Matryoshka Representation Learning allows slicing
            full_vector = memory.embedding.values
            if len(full_vector) > 256:
                memory.embedding_small = EmbeddingVector(
                    values=full_vector[:256],
                    dimensions=256
                )


class DecayService:
    """Domain service for memory decay operations."""

    def __init__(self, memory_service: Optional[MemoryService] = None):
        self.memory_service = memory_service or MemoryService()

    def update_decay_score(self, memory: Memory) -> None:
        """Update the decay score for a single memory.

        This modifies the memory in place.
        """
        if memory.is_archived:
            return

        memory.calculate_decay_score()

        # Check if we should adapt vector dimensions
        # Strategy 82: Adaptive Vector Dimensions
        self.memory_service.adapt_vector_dimensions(memory)

    def should_archive_based_on_decay(self, memory: Memory, threshold: float = 0.1) -> bool:
        """Check if memory should be archived based on decay score."""
        if not memory.decay_score:
            self.update_decay_score(memory)

        # Ensure decay_score is set
        if memory.decay_score and memory.decay_score.value < threshold:
             # Also consider access count and explicit importance
             if memory.access_count == 0 and memory.importance.value < 0.3:
                 return True

        return False


class DeduplicationService:
    """Domain service for detecting and handling duplicate memories."""

    def calculate_content_hash(self, memory: Memory) -> str:
        """Calculate a hash of the memory content."""
        return hashlib.sha256(memory.content.encode('utf-8')).hexdigest()

    def find_exact_duplicates(self, target: Memory, candidates: List[Memory]) -> List[Memory]:
        """Find memories with exact content match."""
        target_hash = self.calculate_content_hash(target)
        duplicates = []

        for candidate in candidates:
            if candidate.id == target.id:
                continue

            if self.calculate_content_hash(candidate) == target_hash:
                duplicates.append(candidate)

        return duplicates

    def find_semantic_duplicates(
        self,
        target: Memory,
        candidates: List[Memory],
        threshold: float = 0.95
    ) -> List[Memory]:
        """Find memories with high semantic similarity.

        Args:
            target: The memory to check against.
            candidates: List of candidate memories.
            threshold: Cosine similarity threshold (default 0.95).
                       Use 0.98 for aggressive deduplication (Strategy 90).
        """
        if not target.embedding:
            return []

        duplicates = []
        target_vec = target.embedding.to_numpy()

        # Pre-calculate target norm to speed up loop
        target_norm = sum(target_vec**2)**0.5

        if target_norm == 0:
             return []

        for candidate in candidates:
            if candidate.id == target.id or not candidate.embedding:
                continue

            # Calculate cosine similarity
            candidate_vec = candidate.embedding.to_numpy()
            candidate_norm = sum(candidate_vec**2)**0.5

            if candidate_norm == 0:
                continue

            similarity = (
                target_vec @ candidate_vec /
                (target_norm * candidate_norm)
            )

            if similarity >= threshold:
                duplicates.append(candidate)

        return duplicates

    def merge_memories(self, target: Memory, source: Memory) -> Memory:
        """Merge source memory metadata/stats into target memory.

        This handles Strategy 90 (Vector Deduplication) where memories
        are merged based on extreme similarity.

        Args:
            target: The memory that will survive.
            source: The duplicate memory that will be archived.

        Returns:
            The updated target memory.
        """
        # Merge access counts
        target.access_count += source.access_count

        # Merge tags (union)
        for tag in source.tags:
            target.add_keyword_tag(tag)

        # Merge metadata
        if source.metadata:
            if "merged_from" not in target.metadata:
                target.metadata["merged_from"] = []
            target.metadata["merged_from"].append(source.id)

            # Merge other metadata keys if not present
            for k, v in source.metadata.items():
                if k not in target.metadata and k != "merged_from":
                    target.metadata[k] = v

        # Update timestamp to reflect activity
        target.updated_at = source.updated_at if source.updated_at > target.updated_at else target.updated_at

        return target


class ConsolidationService:
    """Domain service for memory consolidation."""

    def group_memories_for_consolidation(
        self,
        memories: List[Memory]
    ) -> List[List[Memory]]:
        """Group similar memories that should be consolidated.

        Returns a list of lists, where each inner list contains
        memories that should be merged together.
        """
        # This is a placeholder for more complex clustering logic
        # For now, we group by category if available, or just simple chunks

        groups: Dict[str, List[Memory]] = {}
        ungrouped: List[Memory] = []

        for memory in memories:
            if memory.category:
                if memory.category not in groups:
                    groups[memory.category] = []
                groups[memory.category].append(memory)
            else:
                ungrouped.append(memory)

        result = list(groups.values())
        if ungrouped:
            result.append(ungrouped)

        return result


class EntityService:
    """Domain service for entity operations."""
    
    def extract_entities(self, text: str) -> List[Entity]:
        """Extract entities from text.
        
        This is a placeholder implementation. In production,
        this would call an LLM or NLP service.
        """
        # TODO: Implement actual entity extraction using Gemini
        return []
    
    def find_duplicate_entities(self, entities: List[Entity]) -> List[List[Entity]]:
        """Find duplicate entities based on text similarity."""
        # TODO: Implement entity deduplication logic
        return []


class VectorAttentionService:
    """Domain service for vector attention operations (Strategy 92)."""

    def generate_focus_mask(self, dimensions: int, focus_indices: List[int], weight: float = 2.0) -> List[float]:
        """Generate a mask that focuses on specific dimensions.

        Args:
            dimensions: Size of the vector.
            focus_indices: Indices to weight higher.
            weight: The multiplier for focused indices (default 2.0).

        Returns:
            A list of weights where focused indices have `weight` and others have 1.0.
        """
        mask = [1.0] * dimensions
        for idx in focus_indices:
            if 0 <= idx < dimensions:
                mask[idx] = weight
        return mask

    def generate_segment_mask(self, dimensions: int, segment_start: int, segment_end: int, weight: float = 2.0) -> List[float]:
        """Generate a mask that weights a contiguous segment higher.

        Args:
            dimensions: Size of the vector.
            segment_start: Start index (inclusive).
            segment_end: End index (exclusive).
            weight: The multiplier.
        """
        mask = [1.0] * dimensions
        for i in range(max(0, segment_start), min(dimensions, segment_end)):
            mask[i] = weight
        return mask

    def apply_attention_to_memory(self, memory: Memory, mask: List[float]) -> Memory:
        """Apply an attention mask to a memory's embedding.

        Note: This creates a NEW memory object (or modifies it if mutable,
        but EmbeddingVector is frozen so we replace it).
        """
        if not memory.embedding:
            return memory

        new_embedding = memory.embedding.apply_attention(mask)
        # We need to update the memory with the new embedding.
        # Since Memory is a dataclass, we can modify the field.
        memory.embedding = new_embedding
        return memory
