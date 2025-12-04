from typing import Dict, Any, List, Optional
import logging
import json
from enum import Enum
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class QueryIntent(str, Enum):
    FACTUAL = "factual"        # Simple fact retrieval
    SUMMARY = "summary"        # Summarization of a topic
    ANALYSIS = "analysis"      # Deep dive, reasoning, connection finding
    CREATIVE = "creative"      # Generation, brainstorming
    INSTRUCTION = "instruction" # specific command or SOP execution
    UNKNOWN = "unknown"

class IntentClassifier:
    """
    Service for classifying the intent of a user's query.
    Strategy 30: Query Intent Classification.
    """
    def __init__(self, gemini_client: GeminiClient):
        self.gemini_client = gemini_client

    async def classify_intent(self, query: str, context_history: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Classify the user's query into a predefined intent category.

        Args:
            query: The user's query string.
            context_history: Optional list of previous interactions for context.

        Returns:
            Dictionary containing 'intent' (str), 'confidence' (float), and 'reasoning' (str).
        """
        try:
            history_text = ""
            if context_history:
                history_text = "Recent Context:\n" + "\n".join([f"- {h}" for h in context_history[-3:]])

            prompt = f"""
            Analyze the following user query and classify its intent into one of these categories:
            - FACTUAL: Asking for specific facts, definitions, or data points.
            - SUMMARY: Requesting a summary or overview of a topic.
            - ANALYSIS: Asking for insights, patterns, reasoning, relationships, or deep understanding.
            - CREATIVE: Asking for content generation, brainstorming, or fictional scenarios.
            - INSTRUCTION: Giving a specific command, asking to execute a procedure or SOP.

            {history_text}

            User Query: "{query}"

            Output a JSON object with the following fields:
            - "intent": One of [FACTUAL, SUMMARY, ANALYSIS, CREATIVE, INSTRUCTION]
            - "confidence": float between 0.0 and 1.0
            - "reasoning": Brief explanation of why this category was chosen.
            """

            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="classification",
                temperature=0.0
            )

            content = response.get("content", "").strip()
            # Handle potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()

            result = json.loads(content)

            # Normalize intent string to lowercase enum value
            intent_str = result.get("intent", "UNKNOWN").lower()
            if intent_str not in [i.value for i in QueryIntent]:
                intent_str = "unknown"

            result["intent"] = intent_str
            return result

        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return {
                "intent": QueryIntent.UNKNOWN.value,
                "confidence": 0.0,
                "reasoning": f"Classification failed: {e}"
            }
