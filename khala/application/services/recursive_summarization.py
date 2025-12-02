"""Application service for recursive summarization.

This service implements hierarchical summary generation (Strategy 150).
It takes a collection of memories, groups them, and generates summaries recursively.
"""

import logging
from typing import List, Optional, Dict, Any
from khala.domain.memory.entities import Memory, MemoryTier
from khala.domain.memory.repository import MemoryRepository
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class RecursiveSummarizationService:
    def __init__(
        self,
        repository: MemoryRepository,
        gemini_client: GeminiClient,
    ):
        self.repository = repository
        self.gemini_client = gemini_client

    async def summarize_recursively(
        self,
        memories: List[Memory],
        user_id: str,
        group_size: int = 5
    ) -> Memory:
        """
        Recursively summarizes a list of memories until a single summary memory remains.

        Args:
            memories: List of memories to summarize.
            user_id: The user ID.
            group_size: Number of memories to group together for one summary step.

        Returns:
            The final high-level summary memory.
        """
        if not memories:
            raise ValueError("No memories provided for summarization")

        # Base case: if we have 1 memory.
        if len(memories) == 1:
             # If it's already a summary (has summary_level > 0) or we treat it as the result
             # But if the caller passes a single raw memory, maybe they want a summary of it?
             # For recursion purposes, returning the single memory is correct.
             return memories[0]

        # We process in layers.
        current_layer = memories

        # Determine starting level based on inputs
        current_level = max((getattr(m, 'summary_level', 0) for m in current_layer), default=0)

        while len(current_layer) > 1:
            next_layer = []

            # Chunk the current layer
            for i in range(0, len(current_layer), group_size):
                chunk = current_layer[i : i + group_size]

                # If only 1 item in chunk and it's the only chunk, we are done?
                # No, the loop condition len(current_layer) > 1 ensures we have more than 1 item.
                # If we have 6 items and group_size is 5.
                # Chunk 1: 5 items. Chunk 2: 1 item.
                # We summarize Chunk 1.
                # Chunk 2 is just 1 item. Should we summarize it?
                # Or just promote it to next layer?
                # Promoting it might be better if it's already a summary, but if it's raw memory,
                # mixing raw and summary in next layer is confusing.
                # Strategy: Summarize every chunk even if size 1, to maintain level consistency?
                # Or carry over. Let's summarize to be safe and consistent.

                summary_content = await self._generate_summary_for_chunk(chunk)

                new_level = current_level + 1

                new_memory = Memory(
                    user_id=user_id,
                    content=summary_content,
                    tier=MemoryTier.LONG_TERM,
                    importance=0.5,
                    summary_level=new_level,
                    child_memory_ids=[m.id for m in chunk],
                    metadata={
                        "is_recursive_summary": True,
                        "child_count": len(chunk)
                    }
                )

                # Persist the new memory
                # Note: repository.create usually returns ID, but we need the object.
                # The ID is generated in Memory constructor.
                await self.repository.create(new_memory)

                # Update children to point to parent
                for child in chunk:
                    child.parent_summary_id = new_memory.id
                    await self.repository.update(child)

                next_layer.append(new_memory)

            current_layer = next_layer
            current_level += 1

        return current_layer[0]

    async def _generate_summary_for_chunk(self, chunk: List[Memory]) -> str:
        """Generates a summary for a chunk of memories using LLM."""

        contents = [m.content for m in chunk]
        combined_text = "\n\n".join([f"Memory {i+1}:\n{c}" for i, c in enumerate(contents)])

        prompt = f"""
        Analyze the following {len(chunk)} memory items and generate a comprehensive summary that captures the key information, relationships, and context from all of them.

        Items:
        {combined_text}

        Summary:
        """

        # Using gemini-2.0-flash as per typical strategy for speed/cost
        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="generation",
                model_id="gemini-2.0-flash"
            )
            return response.get("content", "").strip()
        except Exception as e:
            logger.error(f"Summarization failed: {e}")
            return "Summary generation failed."
