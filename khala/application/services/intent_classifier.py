"""Intent classification service for search queries."""

import logging
from typing import Optional, List
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class IntentClassifier:
    """Classifies user search queries into Fact, Summary, or Analysis intents."""

    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def classify(self, query: str) -> str:
        """
        Classifies the user query into one of three intents:
        - Fact: The user is looking for a specific fact or data point.
        - Summary: The user wants a summary of a topic or concept.
        - Analysis: The user needs deep understanding, reasoning, or connection of concepts.

        Args:
            query: The user search query.

        Returns:
            One of "Fact", "Summary", "Analysis". Defaults to "Analysis" on failure.
        """
        prompt = f"""
        Classify the following user search query into exactly one of these three categories:
        1. Fact: Asking for specific facts, dates, names, or simple definitions.
        2. Summary: Asking for an overview, summary, or general explanation.
        3. Analysis: Asking for "why", "how", comparisons, reasoning, or complex relationships.

        Query: "{query}"

        Return only the category name (Fact, Summary, or Analysis).
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="classification",
                temperature=0.1
            )

            intent = response.get("content", "").strip()

            # Normalize response
            if "fact" in intent.lower():
                return "Fact"
            elif "summary" in intent.lower():
                return "Summary"
            elif "analysis" in intent.lower():
                return "Analysis"
            else:
                logger.warning(f"Unexpected intent classification: {intent}. Defaulting to Analysis.")
                return "Analysis"

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return "Analysis"
