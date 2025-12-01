import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, replace
from enum import Enum

from khala.domain.memory.entities import Memory

logger = logging.getLogger(__name__)

class ConflictType(Enum):
    CONTENT_MISMATCH = "content_mismatch"
    METADATA_MISMATCH = "metadata_mismatch"
    DELETION_IN_INCOMING = "deletion_in_incoming" # Exists in base, not in incoming
    ADDITION_IN_INCOMING = "addition_in_incoming" # Exists in incoming, not in base

@dataclass
class MergeConflict:
    memory_id: str
    conflict_type: ConflictType
    base_version: Optional[Memory]
    incoming_version: Optional[Memory]
    description: str

class ResolutionStrategy(Enum):
    KEEP_BASE = "keep_base"
    KEEP_INCOMING = "keep_incoming"
    MERGE_LLM = "merge_llm"

class MergeService:
    """Service for merge conflict resolution (Strategy 158)."""

    def detect_conflicts(
        self,
        base_memories: List[Memory],
        incoming_memories: List[Memory]
    ) -> List[MergeConflict]:
        """Detect conflicts between two sets of memories (representing branches)."""

        base_map = {m.id: m for m in base_memories}
        incoming_map = {m.id: m for m in incoming_memories}

        conflicts = []

        base_ids = set(base_map.keys())
        incoming_ids = set(incoming_map.keys())

        common_ids = base_ids & incoming_ids
        only_base_ids = base_ids - incoming_ids
        only_incoming_ids = incoming_ids - base_ids

        # Check intersection for content mismatches
        for mid in common_ids:
            base_mem = base_map[mid]
            inc_mem = incoming_map[mid]

            # Check content
            if base_mem.content != inc_mem.content:
                conflicts.append(MergeConflict(
                    memory_id=mid,
                    conflict_type=ConflictType.CONTENT_MISMATCH,
                    base_version=base_mem,
                    incoming_version=inc_mem,
                    description="Content differs between branches."
                ))

        # Check deletions (informational/conflict?)
        for mid in only_base_ids:
             conflicts.append(MergeConflict(
                memory_id=mid,
                conflict_type=ConflictType.DELETION_IN_INCOMING,
                base_version=base_map[mid],
                incoming_version=None,
                description="Memory exists in Base but not in Incoming."
            ))

        # Check additions
        for mid in only_incoming_ids:
             conflicts.append(MergeConflict(
                memory_id=mid,
                conflict_type=ConflictType.ADDITION_IN_INCOMING,
                base_version=None,
                incoming_version=incoming_map[mid],
                description="Memory exists in Incoming but not in Base."
            ))

        return conflicts

    async def resolve_conflict(
        self,
        conflict: MergeConflict,
        strategy: ResolutionStrategy,
        gemini_client: Any = None
    ) -> Optional[Memory]:
        """Resolve a single conflict."""

        if strategy == ResolutionStrategy.KEEP_BASE:
            return conflict.base_version

        elif strategy == ResolutionStrategy.KEEP_INCOMING:
            return conflict.incoming_version

        elif strategy == ResolutionStrategy.MERGE_LLM:
            if not gemini_client:
                raise ValueError("GeminiClient required for LLM merge")

            if not conflict.base_version or not conflict.incoming_version:
                 return conflict.base_version or conflict.incoming_version

            # Use LLM to merge
            prompt = f"""
            Merge these two conflicting versions of a memory into one coherent version.

            Version A (Base):
            {conflict.base_version.content}

            Version B (Incoming):
            {conflict.incoming_version.content}

            Merged Version:
            """

            try:
                response = await gemini_client.generate_text(
                    prompt=prompt,
                    task_type="generation",
                    model_id="gemini-2.5-pro"
                )
                merged_content = response.get("content", "").strip()

                # We need to return a new Memory object with merged content.
                merged_memory = replace(conflict.base_version)
                merged_memory.content = merged_content
                # Update metadata to reflect merge
                merged_memory.metadata = merged_memory.metadata.copy() # Shallow copy dict
                merged_memory.metadata["merge_history"] = "merged_llm"
                return merged_memory

            except Exception as e:
                logger.error(f"LLM Merge failed: {e}")
                return conflict.base_version # Fallback

        return None
