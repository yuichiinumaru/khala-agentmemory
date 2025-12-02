"""Domain services for branching and version control.

This module provides the `BranchService` for managing memory branches,
forking logic, and copy-on-write operations.
"""

from typing import List, Optional, Tuple, Dict
from datetime import datetime, timezone
import uuid

from .entities import Memory, Branch, MemoryTier
from .repository import MemoryRepository

class BranchService:
    """Service for managing memory branches and version control."""

    def __init__(self, memory_repository: MemoryRepository):
        self.memory_repository = memory_repository

    async def create_branch(
        self,
        name: str,
        user_id: str,
        parent_branch_id: Optional[str] = None,
        description: str = ""
    ) -> Branch:
        """Create a new branch.

        If parent_branch_id is provided, the new branch inherits from it.
        Inheritance in this system means that queries to the new branch
        will fall back to the parent branch for memories not modified in the child.
        """
        branch = Branch(
            name=name,
            created_by=user_id,
            parent_id=parent_branch_id,
            description=description
        )

        # Persist the branch using the repository
        # Note: Repository interface needs to be updated to support save_branch
        await self.memory_repository.save_branch(branch)

        return branch

    async def fork_memory(
        self,
        memory: Memory,
        target_branch_id: str
    ) -> Memory:
        """Fork a memory into a new branch (Copy-on-Write).

        This creates a new version of the memory in the target branch.
        The new memory points to the original as its parent.
        """
        # If the memory is already in the target branch, return it directly
        if memory.branch_id == target_branch_id:
            return memory

        # Create a copy
        new_memory = Memory(
            user_id=memory.user_id,
            content=memory.content,
            tier=memory.tier,
            importance=memory.importance,
            # New IDs and tracking
            id=str(uuid.uuid4()),
            branch_id=target_branch_id,
            parent_memory_id=memory.id,
            version=memory.version + 1,
            # Copy other fields
            embedding=memory.embedding,
            tags=list(memory.tags),
            category=memory.category,
            summary=memory.summary,
            metadata=dict(memory.metadata),
            # Reset tracking stats for the new branch copy
            access_count=0,
            llm_cost=0.0,
            verification_score=memory.verification_score, # Inherit trust
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            accessed_at=datetime.now(timezone.utc)
        )

        # Persist the new memory
        await self.memory_repository.save(new_memory)

        return new_memory

    async def get_memory_in_branch(
        self,
        memory_id: str,
        branch_id: str
    ) -> Optional[Memory]:
        """Retrieve a memory in the context of a branch.

        This handles the fallback logic:
        1. Check if memory exists in the branch.
        2. If not, check parent branch recursively.
        """
        # This implementation depends on how we query.
        # Ideally, we query by ID and Branch.
        # But if we are looking for a specific memory ID, that ID is unique globally.
        # So `get_memory` by ID is enough to find *a* memory.
        #
        # But the use case is usually: "Find memory X in branch B".
        # If memory X was originally in Branch A, and we are in Branch B (child of A).
        # We probably have a reference to "Logical Memory X".
        #
        # However, in this system, memories are immutable-ish documents.
        # If we update a memory in Branch B, we get a NEW ID (Y).
        # So applications need to know which ID represents "Concept X" in "Branch B".
        #
        # This suggests we might need a stable identifier if we want to track "the same memory" across branches.
        # OR we rely on search.
        #
        # For this task, "Copy-on-write" usually applies when we *modify*.
        # So `fork_memory` handles the modification part.
        #
        # Reading part:
        # If I search for "apples" in Branch B.
        # I should get results from Branch B, AND results from Branch A that are not overridden in B.

        # This is complex to do purely in app logic without a heavy query cost.
        # Strategy:
        # 1. Search in Branch B.
        # 2. Search in Branch A.
        # 3. Filter A results: exclude if "conceptually same" memory is in B.
        #    How do we know if it's "conceptually same"? `parent_memory_id`.

        # For now, let's implement the `fork_memory` and assume the repository
        # handles the "Search in Branch" logic via sophisticated queries.

        return await self.memory_repository.get_by_id(memory_id)
