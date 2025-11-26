"""Domain service for query expansion and multi-perspective search."""

import logging
import json
from typing import List
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class QueryExpander:
    """Service for generating multiple perspectives of a search query."""
    
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client
        
    async def generate_perspectives(self, query: str, num_variations: int = 3) -> List[str]:
        """
        Generate multiple variations of a query to capture different perspectives.
        """
        prompt = f"""
        Original Query: "{query}"
        
        Generate {num_variations} different search queries that explore this topic from different angles (e.g., factual, conceptual, practical, historical).
        Return ONLY a JSON list of strings.
        Example: ["query 1", "query 2", "query 3"]
        """
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-2.0-flash",
                temperature=0.7 # Higher temperature for creativity
            )
            
            content = response["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            variations = json.loads(content)
            if isinstance(variations, list):
                return variations[:num_variations]
            return [query]
            
        except Exception as e:
            logger.error(f"Error generating query perspectives: {e}")
            return [query]
