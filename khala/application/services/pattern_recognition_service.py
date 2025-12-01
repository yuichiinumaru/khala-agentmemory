from typing import List, Dict, Any
import logging
import json
import asyncio
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.application.utils import parse_json_safely

logger = logging.getLogger(__name__)

class PatternRecognitionService:
    """
    Service for recognizing cross-session patterns and recurring interests.
    """
    def __init__(self, gemini_client: GeminiClient, db_client: SurrealDBClient):
        self.gemini_client = gemini_client
        self.db_client = db_client

    async def analyze_patterns(self, user_id: str, lookback_limit: int = 50) -> List[Dict[str, Any]]:
        """
        Analyze user's search history to find recurring patterns or interests.

        Args:
            user_id: The user ID to analyze.
            lookback_limit: Number of past sessions to analyze.

        Returns:
            List of detected patterns/interests with confidence scores.
        """
        try:
            sessions = await self.db_client.get_user_sessions(user_id=user_id, limit=lookback_limit)

            # Need at least 3 sessions for meaningful pattern recognition
            if len(sessions) < 3:
                return []

            # Format data for LLM
            history_data = []
            for s in sessions:
                history_data.append(f"Time: {s.get('timestamp')}, Query: {s.get('query')}")

            history_block = "\n".join(history_data)

            prompt = f"""
            Analyze the following user search history and identify recurring patterns, interests, or long-term research goals.

            History:
            {history_block}

            Output a JSON list of objects, where each object represents a pattern:
            [
                {{
                    "pattern_name": "Name of interest/pattern",
                    "description": "Brief description",
                    "confidence": 0.0 to 1.0,
                    "frequency": "high/medium/low",
                    "related_keywords": ["kw1", "kw2"]
                }}
            ]
            """

            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="analysis",
                temperature=0.2
            )

            result = parse_json_safely(response.get("content", ""))
            if isinstance(result, list):
                return result
            return []

        except Exception as e:
            logger.error(f"Pattern recognition failed: {e}")
            return []
