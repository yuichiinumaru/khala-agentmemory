"""Service for generating counterfactual simulations ("What if" scenarios).

Counterfactual Simulation (Strategy 130):
Generating alternative scenarios based on existing memories to explore potential outcomes.
"""

import logging
import uuid
from typing import List, Optional, Dict, Any

from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
from khala.domain.memory.repository import MemoryRepository
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class CounterfactualService:
    """Service to generate counterfactual 'What If' scenarios."""

    def __init__(
        self,
        repository: MemoryRepository,
        gemini_client: Optional[GeminiClient] = None
    ):
        self.repository = repository
        self.gemini_client = gemini_client or GeminiClient()

    async def generate_counterfactuals(
        self,
        memory_id: str,
        what_if_prompt: str,
        num_scenarios: int = 1
    ) -> List[Memory]:
        """Generate counterfactual scenarios for a given memory.

        Args:
            memory_id: The ID of the memory to simulate from.
            what_if_prompt: The specific "what if" change (e.g., "What if the price was 50% higher?").
            num_scenarios: Number of scenarios to generate.

        Returns:
            List of generated counterfactual Memory objects (not yet saved to DB).
        """
        original_memory = await self.repository.get_by_id(memory_id)
        if not original_memory:
            raise ValueError(f"Memory {memory_id} not found")

        prompt = f"""
        Original Scenario:
        {original_memory.content}

        Counterfactual Hypothesis:
        {what_if_prompt}

        Task:
        Generate {num_scenarios} detailed counterfactual scenario(s) based on the hypothesis.
        Explore the consequences and causality.

        Return the scenarios as a list of strings.
        Do not number them if there is only one.
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                task_type="generation",
                model_id="gemini-2.0-flash",
                temperature=0.8 # Higher temperature for creative exploration
            )

            content = response.get("content", "").strip()

            # Simple parsing (assuming the model might number them 1. 2. etc if num_scenarios > 1)
            # For robustness, we might want structured output, but for now we'll treat the whole text
            # as one scenario or split by double newlines if requested multiple.

            scenarios = []
            if num_scenarios > 1:
                # Naive split, might need better logic or asking for JSON
                parts = content.split("\n\n")
                scenarios = [p.strip() for p in parts if p.strip()]
            else:
                scenarios = [content]

            generated_memories = []
            for scenario in scenarios:
                new_memory = Memory(
                    user_id=original_memory.user_id,
                    content=scenario,
                    tier=MemoryTier.WORKING, # Ephemeral nature
                    importance=ImportanceScore.medium(),
                    metadata={
                        "type": "counterfactual",
                        "original_memory_id": memory_id,
                        "hypothesis": what_if_prompt,
                        "is_simulation": True
                    },
                    tags=original_memory.tags + ["counterfactual", "simulation"]
                )
                generated_memories.append(new_memory)

            return generated_memories

        except Exception as e:
            logger.error(f"Failed to generate counterfactuals: {e}")
            raise

    async def save_simulation(self, memories: List[Memory]) -> List[str]:
        """Save generated counterfactual memories to the repository."""
        ids = []
        for memory in memories:
            try:
                # Ensure we don't overwrite the ID if it was auto-generated
                res = await self.repository.create(memory)
                ids.append(res)
            except Exception as e:
                logger.error(f"Failed to save simulation memory: {e}")
        return ids
