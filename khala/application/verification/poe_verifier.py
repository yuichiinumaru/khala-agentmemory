import math
import logging
import asyncio
from typing import List
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.gemini.models import GEMINI_FAST
from khala.domain.prompt.utils import System, User

logger = logging.getLogger(__name__)

class PoEVerifier:
    """Product of Experts Verifier."""

    def __init__(self, client: GeminiClient):
        self.client = client

    async def verify(self, content: str, perspectives: List[str] = None) -> float:
        """
        Verify content using Product of Experts.
        Returns geometric mean of confidence scores (0.0 to 1.0).
        """
        if not perspectives:
            perspectives = [
                "Factual Accuracy",
                "Logical Consistency",
                "Contextual Relevance"
            ]

        tasks = [self._score_perspective(content, p) for p in perspectives]
        scores = await asyncio.gather(*tasks)

        # Filter failures (0.0 scores)
        if any(s < 0.1 for s in scores):
            return 0.0

        # Geometric Mean
        product = 1.0
        for s in scores:
            product *= s

        return math.pow(product, 1.0 / len(scores))

    async def _score_perspective(self, content: str, perspective: str) -> float:
        prompt = (
            System(f"You are a critical verifier focusing on: {perspective}. Rate the content from 0.0 to 1.0.") /
            User(f"Content: {content}\n\nOutput only the numeric score.")
        )
        try:
            res = await self.client.generate_text(str(prompt), model_id=GEMINI_FAST)
            score_str = res.get("content", "0.0").strip()
            return float(score_str)
        except Exception:
            return 0.5 # Neutral fallback
