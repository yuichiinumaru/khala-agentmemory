from typing import List, Optional, Dict, Any
import logging
from datetime import datetime, timezone
import random

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.domain.memory.entities import Memory, MemorySource, Sentiment
from khala.domain.memory.value_objects import MemoryTier, ImportanceScore

logger = logging.getLogger(__name__)

class DreamService:
    """
    Implements Module 12.D.1: Dream & Simulation.
    - Strategy 129: Dream-Inspired Consolidation
    - Strategy 130: Counterfactual Simulation
    """

    def __init__(self, db_client: SurrealDBClient, llm_client: GeminiClient):
        self.db_client = db_client
        self.llm_client = llm_client

    async def consolidate_dreams(self, agent_id: str = "system", memory_count: int = 5) -> Optional[Memory]:
        """
        Strategy 129: Dream-Inspired Consolidation.
        Fetches a mix of recent and random memories to generate loose associations ("dreams").
        """
        logger.info(f"Starting dream consolidation for agent {agent_id}")

        # 1. Fetch memories (Mix of recent and random to simulate dream-like state)
        # We'll fetch more than needed and sample, or use a specific query if available.
        # For now, let's get some recent ones and some random ones if possible,
        # but SurrealDB random fetch might need a specific query.
        # Let's simple fetch recent 20 and pick random 5 for now to simulate "day residue".

        # TODO: Ideally use a custom query for random sampling efficiently
        recent_memories = await self.db_client.search_memories(
            query="*", # Wildcard to get anything
            limit=20,
            filters={}
            # sorting by created_at DESC is default usually, or we can enforce it if needed,
            # but search_memories might rely on vector search if query is text.
            # Here we might want just "get latest memories".
            # The current client might not have a pure "list all" without vector search easily accessible
            # without a raw query. Let's try a generic search or raw query.
        )

        if not recent_memories:
            logger.warning("No memories found to dream about.")
            return None

        selected_memories = random.sample(recent_memories, min(len(recent_memories), memory_count))

        memory_texts = [f"- [{m.created_at}] {m.content}" for m in selected_memories]
        context_str = "\n".join(memory_texts)

        # 2. Generate Dream Content
        prompt = f"""
        You are an AI dreaming. Below are fragments of memories from the recent past.
        Your task is to synthesize them into a "dream" - a loose association, a creative narrative,
        or a surreal combination that highlights hidden connections or emotional themes.

        Memories:
        {context_str}

        Generate a "Dream" narrative (max 200 words) and a brief "Analysis" of what this dream might mean
        for the agent's learning or state.

        Output format:
        Dream: <narrative>
        Analysis: <analysis>
        """

        response = await self.llm_client.generate_content(prompt)

        # 3. Store as a REFLECTION memory
        dream_content = response.text if response else "The dream was vague and faded away."

        # Create MemorySource with correct fields
        source_obj = MemorySource(source_type="system", source_id=agent_id, confidence=1.0)

        dream_memory = Memory(
            user_id=agent_id,
            content=dream_content,
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.high(),
            source=source_obj,
            created_at=datetime.now(timezone.utc),
            metadata={
                "type": "dream_consolidation",
                "strategy_id": "129",
                "source_memories": [str(m.id) for m in selected_memories]
            },
            tags=["dream", "consolidation", "module-12"]
        )

        saved_memory = await self.db_client.create_memory(dream_memory)
        logger.info(f"Dream consolidated and saved: {saved_memory.id}")

        # Optional: Link dream to source memories?
        # Strategy 129 implies associations. We could create edges.
        # But let's stick to the basic implementation first.

        return saved_memory

    async def simulate_counterfactual(self, episode_id: str, agent_id: str = "system") -> Optional[Memory]:
        """
        Strategy 130: Counterfactual Simulation.
        Analyzes an episode and generates "What if" scenarios.
        """
        logger.info(f"Starting counterfactual simulation for episode {episode_id}")

        # 1. Fetch Episode Memories
        # Assuming we can filter by episode_id in metadata or a specific field
        # The audit says Strategy 118 (Episodic Data Model) is Implemented.
        # Let's check Memory entity for episode_id.
        # The memory says "The `Memory` entity now includes `episode_id`".

        episode_memories = await self.db_client.search_memories(
            query="", # Empty query to rely on filters
            filters={"episode_id": episode_id},
            limit=50
        )

        if not episode_memories:
            logger.warning(f"No memories found for episode {episode_id}")
            return None

        # Sort by time to reconstruct narrative
        episode_memories.sort(key=lambda m: m.created_at or datetime.min)

        narrative_texts = [f"- {m.content}" for m in episode_memories]
        narrative_str = "\n".join(narrative_texts)

        # 2. Generate Counterfactual
        prompt = f"""
        Analyze the following sequence of events (Episode):
        {narrative_str}

        Identify a critical decision point or event. Then, simulate a "Counterfactual" scenario:
        "What if X had happened differently?"

        Describe the alternative outcome and what lesson can be learned from this simulation.

        Output format:
        Counterfactual Scenario: <scenario>
        Lesson: <lesson>
        """

        response = await self.llm_client.generate_content(prompt)
        content = response.text if response else "Could not generate simulation."

        # 3. Store as REFLECTION or DECISION (Hypothetical)
        source_obj = MemorySource(source_type="system", source_id=agent_id, confidence=1.0)

        counterfactual_memory = Memory(
            user_id=agent_id,
            content=content,
            tier=MemoryTier.SHORT_TERM,
            importance=ImportanceScore.high(),
            source=source_obj,
            created_at=datetime.now(timezone.utc),
            metadata={
                "type": "counterfactual_simulation",
                "strategy_id": "130",
                "episode_id": episode_id,
                "is_hypothetical": True
            },
            tags=["counterfactual", "simulation", "module-12", f"episode:{episode_id}"]
        )

        saved_memory = await self.db_client.create_memory(counterfactual_memory)
        logger.info(f"Counterfactual simulation saved: {saved_memory.id}")

        return saved_memory
