import logging
from typing import Optional
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class AdaptiveSearchTuner:
    """Dynamically adjusts search parameters based on feedback."""

    def __init__(self, db_client: Optional[SurrealDBClient] = None):
        self.db_client = db_client or SurrealDBClient()
        self.alpha = 0.5
        self.top_k = 10
        self.history = []

    async def log_feedback(self, query: str, success: bool):
        self.history.append((query, success))
        await self._tune()

    async def _tune(self):
        if len(self.history) < 5: return
        recent = self.history[-5:]
        success_rate = sum(1 for _, s in recent if s) / 5

        if success_rate < 0.6:
            # Shift alpha (simple exploration)
            if self.alpha > 0.5:
                self.alpha -= 0.1
            else:
                self.alpha += 0.1

            # Persist
            try:
                # Assuming table 'system_config' or similar
                query = "UPDATE system_config:search_tuner SET alpha=$alpha, top_k=$top_k"
                async with self.db_client.get_connection() as conn:
                    await conn.query(query, {"alpha": self.alpha, "top_k": self.top_k})
            except Exception as e:
                logger.warning(f"Failed to persist tuner state: {e}")
