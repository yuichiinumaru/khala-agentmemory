from typing import List, Dict, Any, Optional
import json
import logging
import asyncio
from khala.domain.memory.entities import Memory
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class SelfChallengingService:
    """
    Implements Strategy 173: Self-Challenging Memory Retrieval.

    This service acts as a 'Skeptic' agent that critiques retrieved memories
    against the user's query to identify hallucinations or irrelevance.
    """

    def __init__(self, gemini_client: GeminiClient):
        self.client = gemini_client

    async def challenge_memories(self, query: str, memories: List[Memory]) -> List[Dict[str, Any]]:
        """
        Challenges a list of retrieved memories against a query.
        Returns a list of results with pass/fail status and reasoning.
        """
        if not memories:
            return []

        # We process in batches to save context window
        results = []
        batch_size = 5

        for i in range(0, len(memories), batch_size):
            batch = memories[i:i+batch_size]
            batch_results = await self._challenge_batch(query, batch)
            results.extend(batch_results)

        return results

    async def _challenge_batch(self, query: str, batch: List[Memory]) -> List[Dict[str, Any]]:
        """
        Internal method to challenge a batch of memories.
        """

        # Prepare context for the LLM
        memory_context = ""
        for idx, mem in enumerate(batch):
            content_preview = mem.content[:300] + "..." if len(mem.content) > 300 else mem.content
            memory_context += f"MEMORY_{idx} (ID: {mem.id}): {content_preview}\n"

        prompt = f"""
        You are a SKEPTIC verifying memory retrieval for an AI agent.

        USER QUERY: "{query}"

        RETRIEVED MEMORIES:
        {memory_context}

        TASK:
        For each memory, determine if it is RELEVANT and FACTUALLY CONSISTENT with the query context.
        Be skeptical. If a memory seems to be a hallucination (e.g. talking about a different topic) or irrelevant, mark it as FAILED.

        OUTPUT FORMAT:
        Return a JSON list of objects. Each object must have:
        - "memory_index": (int) The index of the memory in the list (0 to {len(batch)-1})
        - "status": (str) "PASS" or "FAIL"
        - "reason": (str) Brief explanation of why it passed or failed.
        - "confidence": (float) 0.0 to 1.0 score of your assessment.

        JSON OUTPUT:
        """

        try:
            response = await self.client.generate_content(prompt)
            # Use the robust parser from utils if available, or manual extraction
            from khala.application.utils import parse_json_safely
            parsed = parse_json_safely(response)

            # Map back to memory IDs
            final_results = []
            if isinstance(parsed, list):
                for item in parsed:
                    idx = item.get("memory_index")
                    if idx is not None and 0 <= idx < len(batch):
                        mem = batch[idx]
                        final_results.append({
                            "memory_id": mem.id,
                            "status": item.get("status", "FAIL"),
                            "reason": item.get("reason", "Parsing error"),
                            "confidence": item.get("confidence", 0.0),
                            "original_memory": mem
                        })
            return final_results

        except Exception as e:
            logger.error(f"Error in self-challenge: {e}")
            # Fail open (return memories as is, but marked as unchecked)
            return [{"memory_id": m.id, "status": "UNCHECKED", "reason": str(e), "original_memory": m} for m in batch]

    async def filter_memories(self, query: str, memories: List[Memory], threshold: float = 0.7) -> List[Memory]:
        """
        High-level method to filter out bad memories.
        """
        challenge_results = await self.challenge_memories(query, memories)

        valid_memories = []
        for res in challenge_results:
            if res["status"] == "PASS" and res["confidence"] >= threshold:
                valid_memories.append(res["original_memory"])
            elif res["status"] == "UNCHECKED":
                 valid_memories.append(res["original_memory"])

        return valid_memories
