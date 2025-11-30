from typing import Dict, Any, List, Optional
import logging
import json
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class TopicDetectionService:
    """
    Service for detecting topic changes in a user's session.
    """
    def __init__(self, gemini_client: GeminiClient, db_client: SurrealDBClient):
        self.gemini_client = gemini_client
        self.db_client = db_client

    async def detect_topic_change(self, current_query: str, user_id: str) -> Dict[str, Any]:
        """
        Detect if the current query represents a shift in topic compared to recent history.

        Args:
            current_query: The new query from the user.
            user_id: User ID to fetch session history.

        Returns:
            Dictionary with 'changed' (bool), 'reason' (str), 'previous_topic' (str), 'current_topic' (str).
        """
        try:
            # 1. Fetch recent sessions
            recent_sessions = await self.db_client.get_user_sessions(user_id=user_id, limit=5)

            if not recent_sessions:
                return {
                    "changed": True,
                    "reason": "No previous history found.",
                    "previous_topic": None,
                    "current_topic": "New Session"
                }

            # Extract recent queries
            history_text = "\n".join([f"- {s.get('query')}" for s in recent_sessions])

            # 2. Use LLM to analyze
            prompt = f"""
            Analyze the following sequence of search queries and determine if the LATEST query represents a significant change in topic compared to the previous ones.

            Previous Queries:
            {history_text}

            Latest Query:
            "{current_query}"

            Output a JSON object with the following fields:
            - "changed": boolean (true if topic changed, false if follow-up or related)
            - "previous_topic": string (summary of previous topic)
            - "current_topic": string (summary of current topic)
            - "reason": string (brief explanation)
            """

            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="classification",
                temperature=0.0
            )

            # Parse JSON from response
            content = response.get("content", "").strip()
            # Handle potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()

            result = json.loads(content)
            return result

        except Exception as e:
            logger.error(f"Topic detection failed: {e}")
            return {
                "changed": False, # Default to assuming continuity on error
                "reason": f"Detection failed: {e}",
                "previous_topic": None,
                "current_topic": None
            }
