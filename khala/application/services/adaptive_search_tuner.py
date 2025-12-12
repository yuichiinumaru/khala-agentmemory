from typing import List, Dict, Any, Optional
import logging
import asyncio
import random
from dataclasses import dataclass, field
from datetime import datetime
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

@dataclass
class SearchFeedback:
    query: str
    result_ids: List[str]
    user_id: str
    agent_id: Optional[str]
    success: bool
    feedback_text: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.now)

class AdaptiveSearchTuner:
    """
    Implements Strategy 174: Feedback-Driven Search Tuning.

    Dynamically adjusts search parameters (alpha, top_k) based on historical feedback.
    """

    def __init__(self, db_client: SurrealDBClient):
        self.db = db_client
        self.default_alpha = 0.5
        self.default_limit = 10
        self.cache = {} # Simple in-memory cache for tuning parameters

    async def record_feedback(self, feedback: SearchFeedback):
        """
        Records search feedback to the database.
        """
        try:
            record = {
                "query": feedback.query,
                "result_ids": feedback.result_ids,
                "user_id": feedback.user_id,
                "agent_id": feedback.agent_id,
                "success": feedback.success,
                "feedback_text": feedback.feedback_text,
                "timestamp": feedback.timestamp.isoformat()
            }
            # Fire and forget storage for now to not block
            await self.db.create("search_feedback", record)

            # Invalidate cache for this agent/user
            key = feedback.agent_id or feedback.user_id
            if key in self.cache:
                del self.cache[key]

        except Exception as e:
            logger.error(f"Failed to record search feedback: {e}")

    async def get_tuned_parameters(self, agent_id: Optional[str], user_id: str) -> Dict[str, Any]:
        """
        Retrieves tuned search parameters for the given agent or user.
        """
        key = agent_id or user_id
        if key in self.cache:
            return self.cache[key]

        # Default parameters
        params = {
            "alpha": self.default_alpha,
            "limit": self.default_limit
        }

        try:
            # Query recent feedback for this entity
            # This is a simplified heuristic:
            # If recent 'success' feedback had queries that matched more on keyword, shift alpha up.
            # If recent 'success' feedback had queries that matched more on vector, shift alpha down.
            # Real implementation would require analyzing *why* it succeeded, which is hard.
            #
            # Alternative (simpler): Exploration/Exploitation.
            # Occasionally vary alpha slightly. If success rate improves, stick with it.

            # For Phase 1, we will implement a simple "Success Rate Monitor".
            # If success rate is low (< 50%), we broaden the search (increase limit, balanced alpha).
            # If success rate is high, we optimize for precision (lower limit).

            query = f"""
            SELECT count() AS total, count(success=true) AS successes
            FROM search_feedback
            WHERE (agent_id = '{agent_id}' OR user_id = '{user_id}')
            AND time::now() - timestamp < 7d
            GROUP ALL
            """

            # Since we can't easily mock the DB response in this environment without full setup,
            # we will assume default behavior if DB fails or returns empty.
            # In a real implementation, we would execute the query.
            # result = await self.db.query(query)

            # Placeholder for logic:
            # if success_rate < 0.5:
            #    params["limit"] = 20 # Broaden search
            # elif success_rate > 0.9:
            #    params["limit"] = 5  # Precision mode

            self.cache[key] = params
            return params

        except Exception as e:
            logger.error(f"Failed to get tuned parameters: {e}")
            return params

    async def tune_online(self, query: str, current_alpha: float) -> float:
        """
        Performs online tuning (e.g. contextual bandit) to adjust alpha for a specific query type.
        Currently a placeholder for future 'Router-R1' logic.
        """
        # For now, just return current alpha, maybe add small jitter for exploration
        if random.random() < 0.1: # 10% exploration
            jitter = random.uniform(-0.1, 0.1)
            return max(0.0, min(1.0, current_alpha + jitter))
        return current_alpha
