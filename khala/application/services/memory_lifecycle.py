"""Application service for memory lifecycle management.

This service orchestrates the lifecycle of memories, including
promotion, decay, consolidation, deduplication, and archival.
"""

import logging
import asyncio
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
from khala.application.services.significance_scorer import SignificanceScorer
from khala.application.services.privacy_safety_service import PrivacySafetyService
from khala.infrastructure.coordination.distributed_lock import SurrealDBLock
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import ModelRegistry

logger = logging.getLogger(__name__)

PROMPT_SUMMARIZE = """Summarize the following content in under 50 words:

{content}"""

PROMPT_CONSOLIDATE = """
Consolidate the following {count} memory fragments into a single, comprehensive memory.
Maintain all key details but remove redundancies.

Memories:
{memory_list}

New Memory Content:
"""

class MemoryLifecycleService:
    """Service to manage the lifecycle of memories."""

    def __init__(
        self,
        repository: MemoryRepository,
        gemini_client: GeminiClient, # Required Dependency
        memory_service: Optional[MemoryService] = None,
        decay_service: Optional[DecayService] = None,
        deduplication_service: Optional[DeduplicationService] = None,
        consolidation_service: Optional[ConsolidationService] = None,
        conflict_resolution_service: Optional[ConflictResolutionService] = None,
        privacy_safety_service: Optional[PrivacySafetyService] = None,
        significance_scorer: Optional[SignificanceScorer] = None
    ):
        self.repository = repository
        if not gemini_client:
             raise ValueError("MemoryLifecycleService requires a GeminiClient instance.")
        self.gemini_client = gemini_client

        self.memory_service = memory_service or MemoryService()
        self.decay_service = decay_service or DecayService()
        self.deduplication_service = deduplication_service or DeduplicationService()
        self.consolidation_service = consolidation_service or ConsolidationService()
        self.conflict_resolution_service = conflict_resolution_service or ConflictResolutionService(repository)
        self.privacy_safety_service = privacy_safety_service or PrivacySafetyService(self.gemini_client)
        self.significance_scorer = significance_scorer or SignificanceScorer(self.gemini_client)

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

        # Strategy 17 & 31: Significance Scoring & Natural Triggers
        if self.significance_scorer:
             new_score = await self.significance_scorer.calculate_significance(memory.content)
             if new_score.value > memory.importance.value:
                 memory.importance = new_score

        # Strategy 37: Emotion-Driven Memory
        if self.significance_scorer and not memory.sentiment:
            memory.sentiment = await self.significance_scorer.analyze_sentiment(memory.content)

        # Strategy 152: Bias Detection
        if check_privacy and self.privacy_safety_service:
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
                response = await self.gemini_client.generate_text(
                    prompt=PROMPT_SUMMARIZE.format(content=memory.content),
                    task_type="generation",
                    model_id="gemini-2.0-flash" # Use fast model
                )
                memory.summary = response.get("content", "").strip()
            except Exception:
                logger.exception("Failed to auto-summarize memory.")

        # Strategy 86: Conflict Resolution
        if self.conflict_resolution_service and memory.embedding:
            try:
                conflicts = await self.conflict_resolution_service.find_potential_conflicts(memory)
                if conflicts:
                    logger.info(f"Detected {len(conflicts)} potential conflicts for memory {memory.id}")
                    if not memory.metadata:
                        memory.metadata = {}
                    memory.metadata["potential_conflicts"] = [c.id for c in conflicts]
                    memory.metadata["conflict_detected"] = True
            except Exception:
                logger.exception("Failed to check conflicts.")

        return await self.repository.create(memory)

    async def run_lifecycle_job(self, user_id: str) -> Dict[str, int]:
        """Run all lifecycle tasks for a user."""
        logger.info(f"Starting lifecycle job for user {user_id}")
        stats = {
            "promoted": 0,
            "decayed": 0,
            "archived": 0,
            "deduplicated": 0,
            "consolidated": 0
        }

        stats["promoted"] = await self.promote_memories(user_id)
        decay_stats = await self.decay_and_archive_memories(user_id)
        stats["decayed"] = decay_stats["decayed"]
        stats["archived"] = decay_stats["archived"]
        stats["deduplicated"] = await self.deduplicate_memories(user_id)

        # 4. Consolidation (Optional/Heavy operation)
        # Assuming repository exposes client for locking. Ideally repo should provide lock method.
        # But lock relies on SurrealDBClient directly.
        if hasattr(self.repository, 'client'):
            lock = SurrealDBLock(self.repository.client, f"consolidation_lock_{user_id}")
            if await lock.acquire():
                try:
                    stats["consolidated"] = await self.consolidate_memories(user_id)
                finally:
                    await lock.release()
            else:
                logger.info(f"Skipping consolidation for user {user_id}: Lock acquired by another process.")
        else:
             logger.warning("Repository does not expose client; skipping distributed lock for consolidation.")
             stats["consolidated"] = await self.consolidate_memories(user_id)

        logger.info(f"Lifecycle job completed for user {user_id}: {stats}")
        return stats

    async def promote_memories(self, user_id: str) -> int:
        """Check and promote memories to the next tier."""
        promoted_count = 0
        for tier in [MemoryTier.WORKING, MemoryTier.SHORT_TERM]:
            memories = await self.repository.get_by_tier(user_id, tier.value, limit=1000)
            for memory in memories:
                if memory.should_promote_to_next_tier():
                    try:
                        old_tier = memory.tier
                        memory.promote()
                        await self.repository.update(memory)
                        promoted_count += 1
                        logger.debug(f"Promoted memory {memory.id} from {old_tier.value} to {memory.tier.value}")
                    except ValueError as e:
                        logger.warning(f"Failed to promote memory {memory.id}: {e}")
        return promoted_count

    async def decay_and_archive_memories(self, user_id: str) -> Dict[str, int]:
        """Update decay scores and archive memories if needed."""
        stats = {"decayed": 0, "archived": 0}
        for tier in MemoryTier:
            memories = await self.repository.get_by_tier(user_id, tier.value, limit=1000)
            for memory in memories:
                self.decay_service.update_decay_score(memory)
                stats["decayed"] += 1

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
                    await self.repository.update(memory)
        return stats

    async def deduplicate_memories(self, user_id: str) -> int:
        """Find and remove duplicate memories."""
        duplicates_removed = 0

        # 1. Exact duplicates (Global)
        try:
            duplicate_groups = await self.repository.find_duplicate_groups(user_id)
            for group in duplicate_groups:
                if len(group) < 2: continue
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
        except Exception:
            logger.exception("Global exact deduplication failed.")

        # 2. Semantic duplicates (Strategy 90: Vector Deduplication)
        processed_ids = set()
        # Reduced limit to avoid O(N^2) explosion
        BATCH_LIMIT = 50

        for tier in [MemoryTier.WORKING, MemoryTier.SHORT_TERM]:
            memories = await self.repository.get_by_tier(user_id, tier.value, limit=BATCH_LIMIT)

            for i, memory in enumerate(memories):
                if memory.id in processed_ids or not memory.embedding: continue
                if memory.is_archived: continue

                # Look ahead in the batch
                candidates = memories[i+1:]
                if not candidates: continue

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

    async def schedule_consolidation(self, user_id: str) -> Dict[str, Any]:
        """Determines if consolidation should run."""
        memories = await self.repository.get_by_tier(
            user_id, MemoryTier.SHORT_TERM.value, limit=500
        )
        count = len(memories)
        should_run = False
        reason = "insufficient_data"

        if count > 50:
            should_run = True
            reason = "volume_threshold_exceeded"

        current_hour = datetime.now(timezone.utc).hour
        if 2 <= current_hour <= 5 and count > 10:
             should_run = True
             reason = "scheduled_maintenance_window"

        if should_run:
            logger.info(f"Consolidation triggered for user {user_id}. Reason: {reason}")
            consolidated = await self.consolidate_memories(user_id, force=True)
            return {"status": "executed", "consolidated_count": consolidated, "reason": reason}

        return {"status": "skipped", "reason": reason}

    async def consolidate_memories(self, user_id: str, force: bool = False) -> int:
        """Consolidate memories with parallel execution."""
        memories = await self.repository.get_by_tier(
            user_id, MemoryTier.SHORT_TERM.value, limit=200
        )

        if not (force or self.memory_service.should_consolidate(memories)):
            return 0

        groups = self.consolidation_service.group_memories_for_consolidation(memories)

        # Limit concurrency to prevent rate limits
        semaphore = asyncio.Semaphore(5)

        async def process_group(group: List[Memory]) -> int:
            if len(group) <= 1:
                return 0

            async with semaphore:
                try:
                    contents = [m.content for m in group]
                    memory_list_str = "\n".join([f'- {c}' for c in contents])

                    response = await self.gemini_client.generate_text(
                        prompt=PROMPT_CONSOLIDATE.format(
                            count=len(contents),
                            memory_list=memory_list_str
                        ),
                        task_type="generation",
                        model_id="gemini-2.5-pro"
                    )
                    new_content = response.get("content", "").strip()

                    if new_content:
                        new_memory = Memory(
                            user_id=user_id,
                            content=new_content,
                            tier=MemoryTier.LONG_TERM,
                            importance=ImportanceScore(0.8),
                            metadata={"consolidated_from": [m.id for m in group]}
                        )
                        await self.repository.create(new_memory)

                        for m in group:
                            m.archive(force=True)
                            m.metadata["consolidated_into"] = new_memory.id
                            await self.repository.update(m)

                        logger.info(f"Consolidated {len(group)} memories into new memory {new_memory.id}")
                        return len(group)
                except Exception:
                    logger.exception("Failed to consolidate group.")
                    return 0
            return 0

        # Run tasks concurrently
        results = await asyncio.gather(*[process_group(g) for g in groups])
        return sum(results)
