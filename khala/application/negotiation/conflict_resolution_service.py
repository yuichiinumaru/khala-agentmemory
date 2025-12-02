from typing import List
from khala.domain.memory import Memory

class ConflictResolutionService:
    """
    A service to resolve conflicts between memories.
    """

    def resolve_conflicts(self, memories: List[Memory]) -> Memory:
        """
        Resolves conflicts between a list of memories and returns the winning memory.
        """
        # For now, we'll use a simple "last-write-wins" strategy.
        # In the future, this will involve a multi-agent debate.
        return memories[-1]
