"""Service for dream-inspired consolidation (Strategy 129).

This service performs 'nightly' loose association forming by selecting
random/unconnected memories and using an LLM to generate creative
narratives or insights that connect them.
"""

import logging
from typing import List, Optional, Dict, Any
import random

from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore, MemorySource
from khala.domain.memory.repository import MemoryRepository
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class DreamConsolidationService:
    """Service for dream-inspired consolidation (Strategy 129)."""

    def __init__(
        self,
        repository: MemoryRepository,
        gemini_client: Optional[GeminiClient] = None
    ):
        self.repository = repository
        self.gemini_client = gemini_client or GeminiClient()

    async def run_dream_cycle(self, user_id: str, count: int = 5) -> Optional[Memory]:
        """Run a single dream cycle.

        Args:
            user_id: The user ID to dream for.
            count: Number of memories to include in the dream.

        Returns:
            The generated dream memory, or None if failed.
        """
        logger.info(f"Starting dream cycle for user {user_id}")

        # 1. Fetch candidates (mix of tiers)
        # We fetch a larger pool to sample from to ensure randomness
        candidates = []
        try:
            for tier in [MemoryTier.LONG_TERM, MemoryTier.SHORT_TERM]:
                memories = await self.repository.get_by_tier(user_id, tier.value, limit=50)
                candidates.extend(memories)
        except Exception as e:
            logger.error(f"Failed to fetch memories for dream cycle: {e}")
            return None

        if len(candidates) < 2:
            logger.info("Not enough memories to dream (need at least 2).")
            return None

        # Select random subset
        selected_memories = random.sample(candidates, k=min(len(candidates), count))

        # 2. Generate Dream Content
        dream_content = await self._generate_dream_content(selected_memories)

        if not dream_content:
            return None

        # 3. Save Dream Memory
        try:
            dream_memory = Memory(
                user_id=user_id,
                content=dream_content,
                tier=MemoryTier.WORKING, # Waking up with a fresh idea
                importance=ImportanceScore(0.5), # Medium importance initially
                category="dream",
                tags=["dream", "generative_consolidation"],
                metadata={
                    "strategy": "129_dream_consolidation",
                    "source_memories": [m.id for m in selected_memories]
                },
                source=MemorySource(
                    source_type="dream",
                    confidence=0.7 # Dreams are fuzzy
                )
            )

            await self.repository.create(dream_memory)
            logger.info(f"Created dream memory {dream_memory.id}")

            return dream_memory
        except Exception as e:
            logger.error(f"Failed to save dream memory: {e}")
            return None

    async def _generate_dream_content(self, memories: List[Memory]) -> Optional[str]:
        """Generate dream content using LLM."""

        memory_texts = "\n".join([f"- {m.content}" for m in memories])

        prompt = f"""
        You are an AI dreaming during a consolidation cycle.
        Here are some fragmented memories from the past:

        {memory_texts}

        Your task:
        1. Find loose, creative, or metaphorical associations between these distinct memories.
        2. Weave them into a single coherent narrative or insight.
        3. Be creative and exploratory. Logic is secondary to insight.

        Output only the narrative/insight.
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="generation",
                # Use a creative model if available, or just Pro
                model_id="gemini-2.5-pro",
                temperature=0.9 # High temperature for dreaming
            )
            return response.get("content", "").strip()
        except Exception as e:
            logger.error(f"Failed to generate dream content: {e}")
            return None
