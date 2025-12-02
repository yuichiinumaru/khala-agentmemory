from typing import List, Dict, Any, Optional
import json
import logging
from datetime import datetime, timezone
import uuid

from khala.domain.memory.entities import Memory, Relationship, MemoryTier
from khala.domain.memory.value_objects import ImportanceScore
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class TaskDecompositionService:
    """
    Service for Hierarchical Task Decomposition (Strategy 53).
    Breaks high-level goals into sub-tasks stored as linked memories.
    """

    def __init__(self, gemini_client: GeminiClient, db_client: SurrealDBClient):
        self.gemini_client = gemini_client
        self.db_client = db_client

    async def decompose_goal(
        self,
        goal: str,
        user_id: str,
        context: Optional[str] = None
    ) -> List[Memory]:
        """
        Decomposes a high-level goal into sub-tasks and stores them as linked memories.

        Args:
            goal: The high-level goal to decompose.
            user_id: The user ID.
            context: Optional context to aid decomposition.

        Returns:
            List of created Memory objects (Goal + Subtasks).
        """
        logger.info(f"Decomposing goal for user {user_id}: {goal[:50]}...")

        # 1. Prompt Gemini to decompose the goal
        prompt = f"""
        You are an expert project manager and AI planner.
        Break down the following high-level goal into 3-7 specific, actionable sub-tasks.

        Goal: {goal}

        {f"Context: {context}" if context else ""}

        Return the result strictly as a JSON list of objects, where each object has:
        - "title": Short title of the subtask
        - "description": Detailed description
        - "estimated_complexity": Low/Medium/High
        - "priority": High/Medium/Low

        Example format:
        [
            {{"title": "Research X", "description": "Find info about X", "estimated_complexity": "Low", "priority": "High"}}
        ]
        """

        try:
            response = await self.gemini_client.generate_text(
                prompt=prompt,
                model_id="gemini-2.5-flash", # Use fast model for planning
                temperature=0.3
            )

            content_text = response["content"]
            # Clean up potential markdown code blocks
            if "```json" in content_text:
                content_text = content_text.split("```json")[1].split("```")[0]
            elif "```" in content_text:
                content_text = content_text.split("```")[1].split("```")[0]

            subtasks_data = json.loads(content_text.strip())

            if not isinstance(subtasks_data, list):
                raise ValueError("LLM response is not a list")

        except Exception as e:
            logger.error(f"Failed to decompose goal via LLM: {e}")
            # Fallback: create single memory for the goal without subtasks
            subtasks_data = []

        # 2. Create Parent Memory (The Goal)
        goal_memory = Memory(
            user_id=user_id,
            content=f"Goal: {goal}",
            tier=MemoryTier.WORKING,
            importance=ImportanceScore(0.9), # High importance for goals
            metadata={
                "type": "goal",
                "status": "active",
                "subtask_count": len(subtasks_data)
            },
            tags=["goal", "planning"]
        )

        goal_id = await self.db_client.create_memory(goal_memory)
        # Update ID in case of deduplication or assignment
        if goal_id:
             # handle memory: prefix if returned by some implementation, though create_memory returns bare ID usually
             if goal_id.startswith("memory:"):
                 goal_id = goal_id.split(":")[1]
             goal_memory.id = goal_id

        created_memories = [goal_memory]

        # 3. Create Subtask Memories and Link to Parent
        for task in subtasks_data:
            subtask_memory = Memory(
                user_id=user_id,
                content=f"Subtask: {task.get('title')}\n\n{task.get('description')}",
                tier=MemoryTier.WORKING,
                importance=ImportanceScore(0.7),
                metadata={
                    "type": "subtask",
                    "parent_goal_id": goal_id,
                    "complexity": task.get("estimated_complexity"),
                    "priority": task.get("priority"),
                    "status": "pending"
                },
                tags=["subtask", "planning"]
            )

            subtask_id = await self.db_client.create_memory(subtask_memory)
            if subtask_id and subtask_id.startswith("memory:"):
                subtask_id = subtask_id.split(":")[1]
            subtask_memory.id = subtask_id
            created_memories.append(subtask_memory)

            # Create Relationship: Subtask -> Goal (subtask_of)
            rel = Relationship(
                from_entity_id=subtask_id,
                to_entity_id=goal_id,
                relation_type="subtask_of",
                strength=1.0,
                valid_from=datetime.now(timezone.utc)
            )
            await self.db_client.create_relationship(rel)

            # Create Relationship: Goal -> Subtask (has_subtask) - Bidirectional
            rel_reverse = Relationship(
                from_entity_id=goal_id,
                to_entity_id=subtask_id,
                relation_type="has_subtask",
                strength=1.0,
                valid_from=datetime.now(timezone.utc)
            )
            await self.db_client.create_relationship(rel_reverse)

        return created_memories
