from typing import List, Optional
import logging
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class QueryExpansionService:
    """
    Service for expanding search queries into multiple perspectives using LLM.
    """
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def expand_query(self, query: str, num_expansions: int = 3) -> List[str]:
        """
        Generate expanded versions of the query to capture different perspectives.

        Args:
            query: Original user query.
            num_expansions: Number of variations to generate.

        Returns:
            List of unique query variations including the original.
        """
        prompt = f"""
        You are an expert search query optimizer.
        Your task is to generate {num_expansions} alternative search queries for the following user input.
        These alternatives should cover exactly these 3 perspectives:
        1. Fact-based: Focus on specific data, definitions, or verified facts.
        2. Summary-oriented: Focus on obtaining an overview or high-level summary.
        3. Deep Analysis: Focus on "why", "how", underlying reasons, and complex relationships.

        User Query: "{query}"

        Output ONLY the alternative queries, one per line. Do not include numbering or explanations.
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="generation",
                temperature=0.7
            )

            content = response.get("content", "").strip()
            variations = [line.strip() for line in content.split('\n') if line.strip()]

            # Ensure original query is included and is first
            unique_variations = [query]
            for v in variations:
                if v.lower() != query.lower() and v not in unique_variations:
                    unique_variations.append(v)

            return unique_variations[:num_expansions + 1]

        except Exception as e:
            logger.error(f"Query expansion failed: {e}")
            return [query]
