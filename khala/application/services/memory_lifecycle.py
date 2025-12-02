"""Application service for memory lifecycle management.

This service orchestrates the lifecycle of memories, including
promotion, decay, consolidation, deduplication, and archival.
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.repository import MemoryRepository
from khala.domain.memory.services import (
    MemoryService,
    DecayService,
    DeduplicationService,
    ConsolidationService,
    ConflictResolutionService
)
from khala.application.services.privacy_safety_service import PrivacySafetyService
from khala.infrastructure.coordination.distributed_lock import SurrealDBLock
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import ModelRegistry

logger = logging.getLogger(__name__)

class MemoryLifecycleService:
    """Service to manage the lifecycle of memories."""

    def __init__(
        self,
        repository: MemoryRepository,
        gemini_client: Optional[GeminiClient] = None,
        memory_service: Optional[MemoryService] = None,
        decay_service: Optional[DecayService] = None,
        deduplication_service: Optional[DeduplicationService] = None,
        consolidation_service: Optional[ConsolidationService] = None,
        conflict_resolution_service: Optional[ConflictResolutionService] = None,
        privacy_safety_service: Optional[PrivacySafetyService] = None
    ):
        self.repository = repository
        self.gemini_client = gemini_client or GeminiClient()
        self.memory_service = memory_service or MemoryService()
        self.decay_service = decay_service or DecayService()
        self.deduplication_service = deduplication_service or DeduplicationService()
        self.consolidation_service = consolidation_service or ConsolidationService()
        self.conflict_resolution_service = conflict_resolution_service or ConflictResolutionService(repository)
        self.privacy_safety_service = privacy_safety_service or PrivacySafetyService(self.gemini_client)

    async def ingest_memory(self, memory: Memory, check_privacy: bool = True) -> str:
        """Ingest a new memory, performing auto-summarization and privacy checks."""

        # Strategy 132: Privacy-Preserving Sanitization
        if check_privacy and self.privacy_safety_service:
            sanitization_result = await self.privacy_safety_service.sanitize_content(memory.content)
            if sanitization_result.was_sanitized:
                memory.content = sanitization_result.sanitized_text
                if not memory.metadata:
                    memory.metadata = {}
                memory.metadata["sanitization_record"] = {
                    "was_sanitized": True,
                    "redacted_items": sanitization_result.redacted_items,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        # Strategy 152: Bias Detection
        if check_privacy and self.privacy_safety_service:
            # We don't block ingestion for bias, but we tag it
            bias_result = await self.privacy_safety_service.detect_bias(memory.content)
            if bias_result.is_biased:
                if not memory.metadata:
                    memory.metadata = {}
                memory.metadata["bias_analysis"] = {
                    "score": bias_result.bias_score,
                    "categories": bias_result.categories,
                    "analysis": bias_result.analysis,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                }

        # Auto-summarize if content is long (> 500 chars) and summary is missing
        if len(memory.content) > 500 and not memory.summary:
            try:
                # Use Gemini Flash for fast summarization
                prompt = f"Summarize the following content in under 50 words:\n\n{memory.content}"
                response = await self.gemini_client.generate_text(
                    prompt=prompt,
                    task_type="generation",
                    model_id=ModelRegistry.get_model("gemini-2.0-flash").model_id
                )
                memory.summary = response.get("content", "").strip()
            except Exception as e:
                logger.warning(f"Failed to auto-summarize memory: {e}")

        # Strategy 86: Conflict Resolution
        # Check for potential conflicts before creation
        if self.conflict_resolution_service and memory.embedding:
            try:
                conflicts = await self.conflict_resolution_service.find_potential_conflicts(memory)
                if conflicts:
                    logger.info(f"Detected {len(conflicts)} potential conflicts for memory {memory.id}")
                    # Tag metadata with conflict info
                    if not memory.metadata:
                        memory.metadata = {}

                    memory.metadata["potential_conflicts"] = [c.id for c in conflicts]
                    memory.metadata["conflict_detected"] = True
            except Exception as e:
                logger.warning(f"Failed to check conflicts: {e}")

        return await self.repository.create(memory)

    async def run_lifecycle_job(self, user_id: str) -> Dict[str, int]:
        """Run all lifecycle tasks for a user.

        Returns a summary of actions taken.
        """
        logger.info(f"Starting lifecycle job for user {user_id}")
        stats = {
            "promoted": 0,
            "decayed": 0,
            "archived": 0,
            "deduplicated": 0,
            "consolidated": 0
        }

        # 1. Promotion
        stats["promoted"] = await self.promote_memories(user_id)

        # 2. Decay & Archival
        decay_stats = await self.decay_and_archive_memories(user_id)
        stats["decayed"] = decay_stats["decayed"]
        stats["archived"] = decay_stats["archived"]

        # 3. Deduplication
        stats["deduplicated"] = await self.deduplicate_memories(user_id)

        # 4. Consolidation (Optional/Heavy operation)
        # We use a distributed lock here to ensure only one instance performs consolidation
        # for a given user at a time.
        lock = SurrealDBLock(self.repository.client, f"consolidation_lock_{user_id}")
        if await lock.acquire():
            try:
                # Placeholder: Consolidation requires LLM integration which is handled separately.
                stats["consolidated"] = await self.consolidate_memories(user_id)
            finally:
                await lock.release()
        else:
            logger.info(f"Skipping consolidation for user {user_id}: Lock acquired by another process.")

        logger.info(f"Lifecycle job completed for user {user_id}: {stats}")
        return stats

    async def promote_memories(self, user_id: str) -> int:
        """Check and promote memories to the next tier."""
        promoted_count = 0

        # Iterate through tiers that can be promoted
        for tier in [MemoryTier.WORKING, MemoryTier.SHORT_TERM]:
            memories = await self.repository.get_by_tier(user_id, tier.value, limit=1000)

            for memory in memories:
                if memory.should_promote_to_next_tier():
                    try:
                        old_tier = memory.tier
                        memory.promote()
                        await self.repository.update(memory)
                        promoted_count += 1
                        logger.debug(
                            f"Promoted memory {memory.id} from {old_tier.value} "
                            f"to {memory.tier.value}"
                        )
                    except ValueError as e:
                        logger.warning(f"Failed to promote memory {memory.id}: {e}")

        return promoted_count

    async def decay_and_archive_memories(self, user_id: str) -> Dict[str, int]:
        """Update decay scores and archive memories if needed."""
        stats = {"decayed": 0, "archived": 0}

        # We need to check all active memories.
        # Since we don't have get_all_active, we iterate by tier.
        for tier in MemoryTier:
            memories = await self.repository.get_by_tier(user_id, tier.value, limit=1000)

            for memory in memories:
                # Update decay score
                self.decay_service.update_decay_score(memory)
                stats["decayed"] += 1

                # Check for archival
                should_archive = (
                    memory.should_archive() or
                    self.decay_service.should_archive_based_on_decay(memory)
                )

                if should_archive and not memory.is_archived:
                    try:
                        memory.archive()
                        await self.repository.update(memory)
                        stats["archived"] += 1
                        logger.debug(f"Archived memory {memory.id}")
                    except ValueError as e:
                        logger.warning(f"Failed to archive memory {memory.id}: {e}")
                else:
                    # Just update the decay score in DB
                    await self.repository.update(memory)

        return stats

    async def deduplicate_memories(self, user_id: str) -> int:
        """Find and remove duplicate memories."""
        duplicates_removed = 0

        # 1. Exact duplicates (Global)
        # Using efficient repository method to find all exact content matches
        try:
            duplicate_groups = await self.repository.find_duplicate_groups(user_id)
            for group in duplicate_groups:
                if len(group) < 2:
                    continue

                # Keep the oldest one (first in list due to ORDER BY created_at ASC)
                original = group[0]
                duplicates = group[1:]

                for dupe in duplicates:
                    if not dupe.is_archived:
                        dupe.archive(force=True)
                        dupe.metadata["duplicate_of"] = original.id
                        dupe.metadata["deduplication_type"] = "exact"
                        await self.repository.update(dupe)
                        duplicates_removed += 1
                        logger.info(f"Archived exact duplicate {dupe.id} of {original.id}")
        except Exception as e:
            logger.error(f"Global exact deduplication failed: {e}")

        # 2. Semantic duplicates (Strategy 90: Vector Deduplication)
        # We iterate by tier for a partial check of recent memories against each other.
        # This is an O(N^2) check on the batch, so we limit the batch size.

        processed_ids = set()

        # Focus on active tiers for semantic dupes
        for tier in [MemoryTier.WORKING, MemoryTier.SHORT_TERM]:
            memories = await self.repository.get_by_tier(user_id, tier.value, limit=200)

            for i, memory in enumerate(memories):
                if memory.id in processed_ids or not memory.embedding:
                    continue

                if memory.is_archived:
                    continue

                candidates = memories[i+1:]

                semantic_dupes = self.deduplication_service.find_semantic_duplicates(
                    memory, candidates
                )

                for dupe in semantic_dupes:
                    if dupe.id not in processed_ids and not dupe.is_archived:
                        dupe.archive(force=True)
                        dupe.metadata["duplicate_of"] = memory.id
                        dupe.metadata["deduplication_type"] = "semantic"
                        await self.repository.update(dupe)
                        duplicates_removed += 1
                        processed_ids.add(dupe.id)
                        logger.info(f"Archived semantic duplicate {dupe.id} of {memory.id}")

        return duplicates_removed

    async def consolidate_memories(self, user_id: str) -> int:
        """Consolidate memories.

        Uses LLM to summarize and merge groups of similar memories.
        """
        consolidated_count = 0

        # Focus on SHORT_TERM tier for consolidation usually
        # Fetch more than threshold (which is > 100 in should_consolidate)
        memories = await self.repository.get_by_tier(
            user_id, MemoryTier.SHORT_TERM.value, limit=200
        )

        if self.memory_service.should_consolidate(memories):
            groups = self.consolidation_service.group_memories_for_consolidation(memories)

            for group in groups:
                if len(group) > 1:
                    try:
                        # 1. Summarize group content
                        contents = [m.content for m in group]
                        memory_list_str = "\n".join([f'- {c}' for c in contents])
                        prompt = f"""
                        Consolidate the following {len(contents)} memory fragments into a single, comprehensive memory.
                        Maintain all key details but remove redundancies.

                        Memories:
                        {memory_list_str}

                        New Memory Content:
                        """

                        # Use the "smart" model (gemini-2.5-pro) which is defined in ModelRegistry
                        response = await self.gemini_client.generate_text(
                            prompt=prompt,
                            task_type="generation",
                            model_id="gemini-2.5-pro"
                        )
                        new_content = response.get("content", "").strip()

                        if new_content:
                            # 2. Create new consolidated memory
                            new_memory = Memory(
                                user_id=user_id,
                                content=new_content,
                                tier=MemoryTier.LONG_TERM, # Promote to long-term
                                importance=0.8, # Reset importance or calculate avg
                                metadata={"consolidated_from": [m.id for m in group]}
                            )
                            # Embed if possible (omitted for brevity, handled by create trigger or separate service usually)

                            await self.repository.create(new_memory)

                            # 3. Archive original memories
                            for m in group:
                                m.archive(force=True)
                                m.metadata["consolidated_into"] = new_memory.id
                                await self.repository.update(m)

                            consolidated_count += len(group)
                            logger.info(f"Consolidated {len(group)} memories into new memory {new_memory.id}")

                    except Exception as e:
                        logger.error(f"Failed to consolidate group: {e}")

        return consolidated_count
