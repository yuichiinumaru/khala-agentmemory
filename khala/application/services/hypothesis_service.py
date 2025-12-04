from typing import List, Dict, Any, Optional
import logging
import json
import uuid
from datetime import datetime, timezone
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class HypothesisService:
    """
    Service for generating and testing hypotheses based on memory data.
    Strategy 54: Hypothesis Testing Framework.
    """
    def __init__(self, gemini_client: GeminiClient, db_client: SurrealDBClient):
        self.gemini_client = gemini_client
        self.db_client = db_client

    async def generate_hypothesis(self, observation: str, context_memories: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate a hypothesis to explain an observation given context.
        """
        context_text = "\n".join([f"- {m.get('content')}" for m in context_memories])

        prompt = f"""
        Given the following observation and context memories, generate a plausible hypothesis that explains the observation.

        Observation: "{observation}"

        Context:
        {context_text}

        Output a JSON object:
        {{
            "hypothesis": "The core hypothesis statement",
            "reasoning": "Why this hypothesis makes sense",
            "confidence": 0.0 to 1.0,
            "evidence_needed": ["What implies this is true?"]
        }}
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="analysis",
                temperature=0.7
            )

            content = response.get("content", "").strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()

            result = json.loads(content)
            return result
        except Exception as e:
            logger.error(f"Hypothesis generation failed: {e}")
            return {"hypothesis": "Failed to generate", "confidence": 0.0}

    async def test_hypothesis(self, hypothesis: str, evidence: List[str]) -> Dict[str, Any]:
        """
        Evaluate a hypothesis against new evidence.
        """
        evidence_text = "\n".join([f"- {e}" for e in evidence])

        prompt = f"""
        Evaluate the validity of the following hypothesis based on the provided evidence.

        Hypothesis: "{hypothesis}"

        Evidence:
        {evidence_text}

        Output a JSON object:
        {{
            "status": "confirmed" | "refuted" | "inconclusive",
            "analysis": "Detailed analysis",
            "confidence": 0.0 to 1.0
        }}
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="analysis",
                temperature=0.0
            )

            content = response.get("content", "").strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()

            result = json.loads(content)
            return result
        except Exception as e:
            logger.error(f"Hypothesis testing failed: {e}")
            return {"status": "error", "analysis": str(e)}
