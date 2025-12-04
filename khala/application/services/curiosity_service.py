"""Curiosity-Driven Exploration Service (Strategy 134).

Identify knowledge holes and generate questions to fill them.
"""

from typing import List, Dict, Any, Optional
import logging
import json
import re

from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class CuriosityService:
    """Service for curiosity-driven exploration."""

    def __init__(self, gemini_client: GeminiClient, db_client: SurrealDBClient):
        self.gemini_client = gemini_client
        self.db_client = db_client

    async def identify_knowledge_gaps(self, topic: str, user_id: str, limit: int = 5) -> List[str]:
        """
        Identify knowledge gaps about a specific topic based on existing memories.

        Args:
            topic: The topic to explore.
            user_id: The user ID to scope the search.
            limit: Number of questions to generate.

        Returns:
            List of questions representing knowledge gaps.
        """
        query = f"SELECT content FROM memory WHERE user_id = $user_id AND content CONTAINS $topic ORDER BY created_at DESC LIMIT 20;"
        params = {"user_id": user_id, "topic": topic.lower()}

        memories_content = []
        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, params)
                # Handle SurrealDB response format (list of dicts, where first element has 'result')
                if result and isinstance(result, list):
                     if len(result) > 0 and 'result' in result[0]:
                         memories_content = [r['content'] for r in result[0]['result'] if 'content' in r]
                     elif len(result) > 0 and 'content' in result[0]: # Direct list
                         memories_content = [r['content'] for r in result if 'content' in r]
        except Exception as e:
            logger.error(f"Failed to retrieve memories for curiosity: {e}")
            return []

        if not memories_content:
            return [f"What is {topic}?", f"Can you explain {topic}?", f"Why is {topic} important?"]

        context_text = "\n".join(memories_content)

        prompt = f"""
        I have the following knowledge about "{topic}":

        {context_text}

        Identify {limit} critical knowledge gaps or missing details about "{topic}" based on the text above.
        Formulate these gaps as inquisitive questions that an agent should ask to learn more.

        Output format: JSON list of strings.
        Example: ["What is the origin of X?", "How does Y relate to Z?"]
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="generation",
                temperature=0.7
            )

            content = response.get("content", "").strip()

            # Extract JSON from markdown if present
            json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
            if json_match:
                content = json_match.group(1)
            else:
                 # Try finding just a list bracket
                 list_match = re.search(r'\[.*\]', content, re.DOTALL)
                 if list_match:
                     content = list_match.group(0)

            questions = json.loads(content)
            if isinstance(questions, list):
                return questions[:limit]
            return []

        except Exception as e:
            logger.error(f"Failed to generate curiosity questions: {e}")
            # Fallback to simple split if JSON fails but text looks like lines
            return [line for line in content.split('\n') if '?' in line][:limit]

    async def generate_inquiry_for_low_confidence(self, user_id: str) -> List[str]:
        """
        Find low confidence memories and generate questions to verify them.
        """
        # Find low confidence memories
        query = "SELECT content FROM memory WHERE user_id = $user_id AND confidence < 0.5 ORDER BY created_at DESC LIMIT 5;"
        params = {"user_id": user_id}

        questions = []
        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, params)
                records = []
                if result and isinstance(result, list):
                    if len(result) > 0 and 'result' in result[0]:
                        records = result[0]['result']
                    elif len(result) > 0 and 'content' in result[0]:
                         records = result

                for record in records:
                    if 'content' not in record:
                        continue

                    content = record['content']
                    # Generate a verification question
                    q_prompt = f"Generate a single question to verify or clarify this uncertain statement: '{content}'"
                    resp = await self.gemini_client.generate_text(q_prompt, temperature=0.3)
                    if resp and resp.get("content"):
                         questions.append(resp["content"].strip())
        except Exception as e:
            logger.error(f"Failed to process low confidence memories: {e}")

        return questions
