"""Service for scoring memory significance.

This service uses LLMs to evaluate the importance of a memory based on its content,
context, and potential future utility.
"""

import logging
import json
from typing import Dict, Any, Optional

from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import ModelRegistry

logger = logging.getLogger(__name__)

class SignificanceScorer:
    """Evaluates memory significance using LLM analysis."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client or GeminiClient()

    async def score_memory(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> float:
        """Calculate a significance score (0.0 - 1.0) for the memory.

        Args:
            content: The memory content string.
            metadata: Optional metadata to provide context.

        Returns:
            Float between 0.0 (trivial) and 1.0 (critical).
        """
        if not content:
            return 0.1

        try:
            prompt = self._build_prompt(content, metadata)

            # Use a faster model (Flash) as this is part of the ingestion loop
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="classification",
                model_id="gemini-2.0-flash",
                temperature=0.0 # Deterministic
            )

            result_text = response.get("content", "").strip()

            # Parse the result
            score = self._parse_score(result_text)
            return score

        except Exception as e:
            logger.error(f"Failed to score memory significance: {e}")
            return 0.5 # Default fallback

    def _build_prompt(self, content: str, metadata: Optional[Dict[str, Any]]) -> str:
        """Construct the evaluation prompt."""
        metadata_str = json.dumps(metadata) if metadata else "{}"

        return f"""
        Analyze the following memory and assign a significance score between 0.0 and 1.0.

        Criteria:
        - 0.0-0.3: Trivial, chit-chat, fleeting context, system noise.
        - 0.4-0.6: General information, preferences, facts with moderate utility.
        - 0.7-0.8: Important facts, specific user instructions, strong preferences, key events.
        - 0.9-1.0: Critical information, urgent tasks, core identity facts, safety-critical info.

        Memory Content:
        "{content}"

        Context Metadata:
        {metadata_str}

        Return ONLY the numeric score (e.g., 0.75). Do not add explanation.
        """

    def _parse_score(self, text: str) -> float:
        """Parse the float score from LLM response."""
        try:
            # Clean up the response
            cleaned = text.strip().replace("Score:", "").replace("score:", "").strip()
            score = float(cleaned)
            return max(0.0, min(1.0, score))
        except ValueError:
            logger.warning(f"Could not parse significance score from: '{text}'")
            return 0.5
