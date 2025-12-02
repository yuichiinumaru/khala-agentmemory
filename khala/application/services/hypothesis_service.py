from typing import List, Dict, Any, Optional
import json
import logging
import asyncio
from datetime import datetime, timezone

from khala.domain.memory.entities import Memory, MemoryTier
from khala.domain.memory.value_objects import ImportanceScore
from khala.infrastructure.gemini.client import GeminiClient
from khala.application.services.hybrid_search_service import HybridSearchService

logger = logging.getLogger(__name__)

class HypothesisService:
    """
    Service for Hypothesis Testing Framework (Strategy 54).
    Agents formulate theories and search memory to prove/disprove.
    """

    def __init__(self, gemini_client: GeminiClient, search_service: HybridSearchService):
        self.gemini_client = gemini_client
        self.search_service = search_service

    async def formulate_hypothesis(self, query: str, context: Optional[str] = None) -> str:
        """
        Formulate a testable hypothesis based on a user query or context.
        """
        prompt = f"""
        Based on the following query and context, formulate a single, testable hypothesis or theory.
        The hypothesis should be a statement that can be verified by searching for evidence.

        Query: {query}
        Context: {context if context else "None"}

        Return ONLY the hypothesis statement.
        """

        response = await self.gemini_client.generate_text(
            prompt=prompt,
            model_id="gemini-2.5-flash",
            temperature=0.4
        )
        return response["content"].strip()

    async def test_hypothesis(
        self,
        hypothesis: str,
        user_id: str,
        search_limit: int = 10
    ) -> Dict[str, Any]:
        """
        Test a hypothesis by searching for evidence and evaluating it.

        Args:
            hypothesis: The hypothesis statement.
            user_id: User ID for memory access.
            search_limit: Number of memories to retrieve.

        Returns:
            Dictionary containing verdict, reasoning, and evidence.
        """
        logger.info(f"Testing hypothesis for user {user_id}: {hypothesis}")

        # 1. Search for evidence (Support and Contradiction)
        # We construct two queries to get a balanced view

        # Search for supporting evidence
        evidence_memories = await self.search_service.search(
            query=f"evidence supporting {hypothesis}",
            user_id=user_id,
            top_k=search_limit,
            vector_weight=1.2 # Bias towards semantic match
        )

        # Format evidence for LLM
        evidence_text = "\n\n".join([
            f"Memory ID: {m.id}\nContent: {m.content}\nConfidence: {getattr(m, 'confidence', 'N/A')}"
            for m in evidence_memories
        ])

        if not evidence_text:
            return {
                "hypothesis": hypothesis,
                "verdict": "Inconclusive",
                "confidence": 0.0,
                "reasoning": "No relevant memories found to test the hypothesis.",
                "evidence_ids": []
            }

        # 2. Evaluate Hypothesis
        prompt = f"""
        You are a rigorous scientific analyst. Evaluate the following hypothesis based ONLY on the provided evidence from memory.

        Hypothesis: {hypothesis}

        Evidence:
        {evidence_text}

        Determine if the hypothesis is:
        - Supported (Evidence strongly confirms it)
        - Contradicted (Evidence refutes it)
        - Inconclusive (Evidence is weak, mixed, or irrelevant)
        - Modified (Evidence suggests a slightly different theory)

        Provide a confidence score (0.0 - 1.0) and a detailed reasoning.

        Return JSON:
        {{
            "verdict": "Supported" | "Contradicted" | "Inconclusive" | "Modified",
            "confidence": float,
            "reasoning": "string",
            "key_evidence_ids": ["id1", "id2"]
        }}
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                model_id="gemini-2.5-pro", # Use smart model for reasoning
                temperature=0.2
            )

            content = response["content"]
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]

            result = json.loads(content.strip())

            # Enrich result
            result["hypothesis"] = hypothesis
            result["all_evidence_count"] = len(evidence_memories)

            return result

        except Exception as e:
            logger.error(f"Hypothesis evaluation failed: {e}")
            return {
                "hypothesis": hypothesis,
                "verdict": "Error",
                "reasoning": f"Evaluation failed: {str(e)}",
                "evidence_ids": []
            }

    async def run_investigation(self, topic: str, user_id: str) -> Dict[str, Any]:
        """
        Full workflow: Formulate -> Test -> Report.
        """
        hypothesis = await self.formulate_hypothesis(topic)
        result = await self.test_hypothesis(hypothesis, user_id)
        return result
