"""
Recursive Summarization Service (Strategy 150).

Implements hierarchical summary generation for large sets of memories.
"""

import logging
import asyncio
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.repository import MemoryRepository
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class RecursiveSummaryService:
    def __init__(self, memory_repo: MemoryRepository, gemini_client: GeminiClient):
        self.memory_repo = memory_repo
        self.gemini_client = gemini_client

    async def summarize_memories(
        self,
        memory_ids: List[str],
        user_id: str,
        chunk_size: int = 5,
        depth: int = 0
    ) -> Memory:
        """
        Recursively summarize a list of memories.

        Args:
            memory_ids: List of memory IDs to summarize.
            user_id: User ID for context and ownership.
            chunk_size: Number of items to summarize in one go.
            depth: Current recursion depth (internal).

        Returns:
            The final summary Memory object.
        """
        if not memory_ids:
            raise ValueError("No memory IDs provided for summarization")

        # 1. Fetch memories
        memories = []
        for mid in memory_ids:
            mem = await self.memory_repo.get_by_id(mid)
            if mem:
                memories.append(mem)

        if not memories:
             raise ValueError("No valid memories found from provided IDs")

        # 2. Base case: if small enough, summarize directly
        if len(memories) <= chunk_size:
            summary_text = await self._generate_summary([m.content for m in memories])
            return await self._save_summary(summary_text, user_id, memories, depth)

        # 3. Recursive step: Chunk and summarize each chunk
        chunks = [memories[i:i + chunk_size] for i in range(0, len(memories), chunk_size)]
        intermediate_summaries = []

        logger.info(f"Recursive summarization depth {depth}: Processing {len(chunks)} chunks")

        for chunk in chunks:
            chunk_content = [m.content for m in chunk]
            summary_text = await self._generate_summary(chunk_content)
            # Store intermediate summary
            summary_mem = await self._save_summary(summary_text, user_id, chunk, depth)
            intermediate_summaries.append(summary_mem)

        # Optimization: If only one summary produced, return it directly
        if len(intermediate_summaries) == 1:
            return intermediate_summaries[0]

        # 4. Recursively summarize the intermediate summaries
        # We pass the IDs of the intermediate summaries we just created
        return await self.summarize_memories(
            [m.id for m in intermediate_summaries],
            user_id,
            chunk_size,
            depth + 1
        )

    async def _generate_summary(self, contents: List[str]) -> str:
        """Generate a summary using Gemini."""
        prompt = "Summarize the following key points into a single cohesive paragraph:\n\n"
        for i, content in enumerate(contents):
            prompt += f"{i+1}. {content}\n"

        response = await self.gemini_client.generate_text(
            prompt,
            task_type="generation" # or summarization if supported
        )
        return response.get("content", "").strip()

    async def _save_summary(
        self,
        summary_text: str,
        user_id: str,
        source_memories: List[Memory],
        depth: int
    ) -> Memory:
        """Save the summary as a new memory."""
        # Link to source memories
        source_ids = [m.id for m in source_memories]

        memory = Memory(
            user_id=user_id,
            content=summary_text,
            tier=MemoryTier.LONG_TERM, # Summaries are generally higher tier
            importance=ImportanceScore.high(), # Summaries are important
            metadata={
                "is_summary": True,
                "recursion_depth": depth,
                "source_memory_ids": source_ids,
                "strategy": "recursive_summarization"
            },
            tags=["summary", "generated"]
        )

        # Save to DB
        await self.memory_repo.create(memory)

        return memory
