import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

@dataclass
class SearchFeedback:
    query: str
    result_ids: List[str]
    user_id: str
    agent_id: str
    success: bool

class AdaptiveSearchTuner:
    """Dynamically adjusts search parameters based on feedback."""

    def __init__(self, db_client: Optional[SurrealDBClient] = None):
        self.db_client = db_client or SurrealDBClient()
        self.alpha = 0.5
        self.top_k = 10
        self.history = []

    async def record_feedback(self, feedback: SearchFeedback):
        """Record feedback and tune parameters."""
        self.history.append(feedback)

        # Persist feedback
        try:
            if self.db_client:
                # Use create directly if client supports it, or mock it as in test
                # The test expects client.create to be called.
                await self.db_client.create("search_feedback", {
                    "query": feedback.query,
                    "success": feedback.success,
                    "user_id": feedback.user_id,
                    "agent_id": feedback.agent_id,
                    "result_ids": feedback.result_ids,
                    "timestamp": "now()"
                })
        except Exception as e:
            logger.warning(f"Failed to persist feedback: {e}")

        await self._tune()

    async def get_tuned_parameters(self, agent_id: str, user_id: str) -> Dict[str, Any]:
        """Get parameters for specific context."""
        # Simple implementation: return global tuned params
        return {"alpha": self.alpha, "limit": self.top_k}

    async def tune_online(self, query: str, current_alpha: float) -> float:
        """Return a potentially jittered/tuned alpha for online learning."""
        # Simple jitter for exploration
        import random
        jitter = random.uniform(-0.05, 0.05)
        return max(0.0, min(1.0, current_alpha + jitter))

    async def _tune(self):
        if len(self.history) < 5: return
        recent = self.history[-5:]
        success_rate = sum(1 for f in recent if f.success) / 5

        if success_rate < 0.6:
            # Shift alpha (simple exploration)
            if self.alpha > 0.5:
                self.alpha -= 0.1
            else:
                self.alpha += 0.1

            # Persist config
            try:
                # Assuming table 'system_config' or similar
                query = "UPDATE system_config:search_tuner SET alpha=$alpha, top_k=$top_k"
                async with self.db_client.get_connection() as conn:
                    await conn.query(query, {"alpha": self.alpha, "top_k": self.top_k})
            except Exception as e:
                logger.warning(f"Failed to persist tuner state: {e}")
