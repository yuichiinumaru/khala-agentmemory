"""Service for calculating memory significance (Strategies 17, 31, 37)."""

import logging
import re
from typing import Dict, Any, Optional

from khala.domain.memory.value_objects import ImportanceScore, Sentiment
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class SignificanceScorer:
    """Calculates significance/importance of memories."""

    def __init__(self, gemini_client: Optional[GeminiClient] = None):
        self.gemini_client = gemini_client or GeminiClient()

    async def calculate_significance(self, content: str, context: Dict[str, Any] = None) -> ImportanceScore:
        """Calculate importance score based on heuristics and LLM analysis.

        Strategy 17: Natural Memory Triggers
        Strategy 31: Significance Scoring
        """

        # Strategy 17: Natural Memory Triggers (Heuristics)
        heuristic_score = self._check_heuristics(content)
        if heuristic_score >= 0.8:
            return ImportanceScore(heuristic_score)

        # Strategy 31: AI Scoring
        # If heuristics are not decisive, use LLM
        # Only use LLM if we have some reasonable length to analyze or if explicitly requested
        if len(content) > 20:
            try:
                llm_score = await self._get_llm_score(content)
                final_score = max(heuristic_score, llm_score)
                return ImportanceScore(min(final_score, 1.0))
            except Exception as e:
                logger.error(f"Error getting LLM significance score: {e}")

        return ImportanceScore(max(heuristic_score, 0.5)) # Default

    def _check_heuristics(self, content: str) -> float:
        """Check for natural language triggers (Strategy 17)."""
        content_lower = content.lower()

        # High priority triggers
        high_triggers = [
            r"remember that", r"important:", r"don't forget",
            r"key takeaway", r"critical", r"crucial", r"must remember",
            r"note to self", r"always remember"
        ]

        for trigger in high_triggers:
            if re.search(trigger, content_lower):
                return 0.9

        # Medium priority triggers
        medium_triggers = [
            r"note that", r"interesting", r"worth noting",
            r"keep in mind", r"summary", r"conclusion"
        ]

        for trigger in medium_triggers:
            if re.search(trigger, content_lower):
                return 0.7

        return 0.3 # Default baseline

    async def _get_llm_score(self, content: str) -> float:
        """Get significance score from Gemini (Strategy 31)."""
        prompt = f"""
        Analyze the importance of the following memory content for a long-term memory system.
        Return ONLY a float between 0.0 and 1.0, where 1.0 is critical information (passwords, key decisions, user preferences) and 0.0 is trivial noise (chitchat).

        Content: "{content}"

        Score:
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="classification", # Treat as classification for fast model
                model_id="gemini-2.0-flash",
                temperature=0.0
            )
            content_text = response.get("content", "")
            # Extract number
            match = re.search(r"0\.\d+|1\.0|0|1", content_text)
            if match:
                return float(match.group())
            return 0.5
        except Exception:
            return 0.5

    async def analyze_sentiment(self, content: str) -> Optional[Sentiment]:
        """Analyze sentiment of the content (Strategy 37)."""
        try:
            result = await self.gemini_client.analyze_sentiment(content)

            return Sentiment(
                score=result.get("score", 0.0),
                label=result.get("label", "neutral"),
                emotions=result.get("emotions", {})
            )
        except Exception as e:
            logger.error(f"Sentiment analysis failed: {e}")
            return None
