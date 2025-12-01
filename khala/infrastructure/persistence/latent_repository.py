"""Repository for LatentMAS (Module 13.3.1)."""

from typing import List, Dict, Any, Optional
from datetime import datetime, timezone
from dataclasses import dataclass

from khala.infrastructure.surrealdb.client import SurrealDBClient

@dataclass
class LatentState:
    agent_id: str
    iteration: int
    state_embedding: List[float]
    decision_made: str
    created_at: datetime

class LatentRepository:
    """Repository for storing and retrieving agent latent states."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def store_state(self, state: LatentState) -> None:
        """Store a latent state vector."""
        query = """
        CREATE latent_states CONTENT {
            agent_id: $agent_id,
            iteration: $iteration,
            state_embedding: $state_embedding,
            decision_made: $decision_made,
            created_at: $created_at
        };
        """
        params = {
            "agent_id": state.agent_id,
            "iteration": state.iteration,
            "state_embedding": state.state_embedding,
            "decision_made": state.decision_made,
            "created_at": state.created_at.isoformat()
        }

        async with self.db_client.get_connection() as conn:
            await conn.query(query, params)

    async def get_latest_state(self, agent_id: str) -> Optional[LatentState]:
        """Get the most recent latent state for an agent."""
        query = """
        SELECT * FROM latent_states
        WHERE agent_id = $agent_id
        ORDER BY created_at DESC
        LIMIT 1;
        """
        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, {"agent_id": agent_id})
            # Deserialization logic (simplified)
            if response and isinstance(response, list) and response:
                items = response
                if isinstance(response[0], dict) and 'result' in response[0]:
                    items = response[0]['result']

                if items:
                    item = items[0]
                    return LatentState(
                        agent_id=item['agent_id'],
                        iteration=item['iteration'],
                        state_embedding=item['state_embedding'],
                        decision_made=item['decision_made'],
                        created_at=datetime.fromisoformat(item['created_at'].replace('Z', '+00:00'))
                    )
        return None
