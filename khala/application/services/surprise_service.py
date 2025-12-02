"""Service for calculating surprise scores for new memories.

Surprise-Based Learning (Strategy 133):
Prioritizes facts that contradict existing models or beliefs.
"""

import logging
import json
from typing import List, Tuple, Optional, Dict, Any

from khala.domain.memory.entities import Memory, ImportanceScore
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import ModelRegistry

logger = logging.getLogger(__name__)

class SurpriseService:
    """Service to calculate surprise scores for new memories."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client or GeminiClient()

    async def calculate_surprise(
        self,
        memory: Memory,
        context_memories: List[Memory]
    ) -> Tuple[float, str]:
        """Calculate the surprise score for a new memory given context.

        Args:
            memory: The new memory being ingested.
            context_memories: Relevant existing memories.

        Returns:
            Tuple containing:
            - Surprise score (0.0 to 1.0)
            - Explanation reason
        """
        if not context_memories:
            return 0.0, "No context available."

        # Filter for high-importance context memories to reduce noise
        # We only care if it contradicts something we strongly believe
        strong_beliefs = [
            m for m in context_memories
            if m.importance.value >= 0.7
        ]

        if not strong_beliefs:
            return 0.0, "No strong beliefs in context."

        context_text = "\n".join([f"- {m.content}" for m in strong_beliefs])

        prompt = f"""
        Analyze the following 'New Information' against the 'Existing Knowledge'.
        Determine if the new information is surprising, unexpected, or contradictory to the existing knowledge.

        Existing Knowledge:
        {context_text}

        New Information:
        {memory.content}

        Rate the 'Surprise Score' from 0.0 (Expected/Consistent) to 1.0 (Highly Unexpected/Contradictory).
        Provide a brief reason.

        Return JSON format:
        {{
            "surprise_score": <float>,
            "reason": "<string>"
        }}
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="analysis",
                model_id="gemini-2.0-flash", # Flash is sufficient for this
                temperature=0.0
            )

            content = response.get("content", "").strip()
            # Clean up potential markdown code blocks
            if content.startswith("```json"):
                content = content.replace("```json", "").replace("```", "")

            result = json.loads(content)
            score = float(result.get("surprise_score", 0.0))
            reason = result.get("reason", "No reason provided.")

            return score, reason

        except Exception as e:
            logger.error(f"Failed to calculate surprise score: {e}")
            return 0.0, f"Error calculating surprise: {e}"

    def apply_surprise_boost(self, memory: Memory, score: float, reason: str) -> None:
        """Apply surprise boost to memory importance and metadata.

        If surprise score > 0.7, boost importance to 1.0 (or high value).
        """
        if score < 0.3:
            return

        memory.metadata["surprise_score"] = score
        memory.metadata["surprise_reason"] = reason

        if score >= 0.7:
            # Boost importance to maximum for high surprise events
            memory.importance = ImportanceScore(1.0)

        logger.info(f"Applied surprise score {score} to memory {memory.id}")
