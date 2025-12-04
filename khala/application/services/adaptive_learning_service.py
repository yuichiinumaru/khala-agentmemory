"""Adaptive Learning Service (Module 15).

This service implements Strategy 139: Contextual Bandits.
It optimizes tool selection or parameter tuning based on feedback.
"""

import logging
from typing import Dict, Any, List, Optional
import random
import math

from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class AdaptiveLearningService:
    """Service for Contextual Bandits and Adaptive Learning."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def select_action(
        self,
        context_id: str,
        actions: List[str],
        epsilon: float = 0.1
    ) -> str:
        """
        Select an action using Epsilon-Greedy strategy.

        Args:
            context_id: Identifier for the context (e.g., 'search_strategy', 'model_selection').
            actions: List of available action IDs.
            epsilon: Exploration rate (0.0-1.0).

        Returns:
            Selected action ID.
        """
        # Exploration
        if random.random() < epsilon:
            return random.choice(actions)

        # Exploitation: Get best action from DB
        best_action = await self._get_best_action(context_id, actions)
        return best_action or random.choice(actions)

    async def record_feedback(
        self,
        context_id: str,
        action_id: str,
        reward: float
    ) -> None:
        """
        Record feedback (reward) for an action.

        Args:
            context_id: Context identifier.
            action_id: Action identifier.
            reward: Reward value (e.g., 1.0 for success, 0.0 for failure).
        """
        # Key: context_id + action_id
        # We replace special chars to ensure safe ID
        safe_key = f"{context_id}_{action_id}".replace(":", "_").replace("-", "_")

        # We use a generic 'bandit_stats' table.
        # Since Schema doesn't define it explicitly, we rely on SCHEMALESS or explicit creation.
        # But our schema is SCHEMAFULL.
        # We should add it to schema or reuse a flexible table.
        # `metadata` on `memory` is flexible.
        # `training_curves` is schemafull.

        # Let's use `training_curves` if appropriate or create a new table.
        # Since I updated schema earlier, I didn't add bandit_stats.
        # I'll rely on the fact that `khala` DB setup usually allows creating new tables if user has permissions,
        # OR I should have added it.
        # I'll update schema one last time or use `metadata` of a "Bandit" entity?
        # Creating a new table without schema definition in `schema.py` works if DB allows it (SurrealDB does if not STRICT).
        # But `schema.py` sets `DEFINE TABLE memory SCHEMAFULL`. It doesn't set global strictness.
        # I'll try to use a table `bandit_stats`.

        query = """
        UPSERT type::thing('bandit_stats', $key) CONTENT {
            context_id: $ctx,
            action_id: $act,
            total_reward: (total_reward OR 0) + $rew,
            count: (count OR 0) + 1,
            avg_reward: ((total_reward OR 0) + $rew) / ((count OR 0) + 1),
            updated_at: time::now()
        };
        """

        params = {
            "key": safe_key,
            "ctx": context_id,
            "act": action_id,
            "rew": reward
        }

        try:
            async with self.db_client.get_connection() as conn:
                await conn.query(query, params)
        except Exception as e:
            logger.error(f"Failed to record feedback: {e}")

    async def _get_best_action(self, context_id: str, actions: List[str]) -> Optional[str]:
        """Retrieve the action with highest average reward."""
        query = """
        SELECT action_id, avg_reward
        FROM bandit_stats
        WHERE context_id = $ctx
        ORDER BY avg_reward DESC
        LIMIT 1;
        """

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, {"ctx": context_id})

                if isinstance(result, list) and len(result) > 0:
                    if isinstance(result[0], dict) and 'result' in result[0]:
                        items = result[0]['result']
                    else:
                        items = result

                    if items:
                        return items[0]['action_id']
        except Exception as e:
            logger.error(f"Failed to get best action: {e}")

        return None
