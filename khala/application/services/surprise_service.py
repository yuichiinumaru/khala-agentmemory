"""Surprise-Based Learning Service (Strategy 133).

Detects contradictions or surprising information to boost memory importance.
"""

from typing import Dict, Any, Optional
import logging
from datetime import datetime, timezone

from khala.infrastructure.gemini.client import GeminiClient
from khala.domain.memory.entities import Memory, ImportanceScore

logger = logging.getLogger(__name__)

class SurpriseService:
    """Service for surprise-based learning."""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def detect_surprise(self, new_content: str, context_content: str) -> float:
        """
        Evaluate if new content is surprising given the context.

        Returns:
            Surprise score (0.0 to 1.0).
        """
        if not context_content:
            return 0.0

        prompt = f"""
        Evaluate the "surprise factor" of the NEW INFORMATION given the KNOWN CONTEXT.

        KNOWN CONTEXT:
        {context_content}

        NEW INFORMATION:
        {new_content}

        Does the new information contradict, significantly update, or reveal something unexpected about the context?
        Rate the surprise on a scale of 0.0 (Expected/Redundant) to 1.0 (Shocking/Contradictory).

        Output ONLY the numeric score.
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="classification",
                temperature=0.1
            )

            content = response.get("content", "").strip()
            # extract number
            import re
            match = re.search(r"0\.\d+|1\.0|0|1", content)
            if match:
                return float(match.group())
            return 0.0

        except Exception as e:
            logger.error(f"Failed to detect surprise: {e}")
            return 0.0

    async def process_memory_surprise(self, memory: Memory, context_memories: list[Memory]) -> None:
        """Update memory importance if surprise is detected."""
        if not context_memories:
            return

        context_text = "\n".join([m.content for m in context_memories])

        score = await self.detect_surprise(memory.content, context_text)

        if score > 0.7:
            # Boost importance
            # Assuming ImportanceScore is immutable value object or float wrapper,
            # we need to set the field on Memory.
            # Memory.importance is ImportanceScore.
            # Strategy says "boost to 1.0 if > 0.7"
            memory.importance = ImportanceScore(1.0)

            if not memory.metadata:
                memory.metadata = {}

            memory.metadata["surprise_score"] = score
            memory.metadata["surprise_detected"] = True
            logger.info(f"Surprise detected (score {score}) for memory {memory.id}. Importance boosted.")
