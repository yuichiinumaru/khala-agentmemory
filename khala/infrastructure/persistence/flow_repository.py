"""Repository for Flow entities (Strategy 116)."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import asdict

from khala.domain.flow.entities import Flow, FlowExecution, FlowStep
from khala.infrastructure.surrealdb.client import SurrealDBClient

class FlowRepository:
    def __init__(self, client: SurrealDBClient):
        self.client = client

    async def save_flow(self, flow: Flow) -> str:
        """Save a flow definition."""
        steps_data = [asdict(step) for step in flow.steps]

        query = """
        CREATE type::thing('flow', $id) CONTENT {
            name: $name,
            description: $description,
            steps: $steps,
            metadata: $metadata,
            is_active: $is_active,
            created_at: $created_at
        };
        """
        params = {
            "id": flow.id,
            "name": flow.name,
            "description": flow.description,
            "steps": steps_data,
            "metadata": flow.metadata,
            "is_active": flow.is_active,
            "created_at": flow.created_at.isoformat()
        }

        async with self.client.get_connection() as conn:
            await conn.query(query, params)
            return flow.id

    async def get_flow(self, flow_id: str) -> Optional[Flow]:
        """Get a flow by ID."""
        query = "SELECT * FROM type::thing('flow', $id);"
        params = {"id": flow_id}

        async with self.client.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list) and len(response) > 0:
                item = response[0]
                if isinstance(item, dict) and 'result' in item:
                    item = item['result'][0] if item['result'] else None

                if not item:
                    return None

                # Reconstruct Flow object
                # Parse steps
                steps = []
                for s_data in item.get('steps', []):
                    steps.append(FlowStep(**s_data))

                return Flow(
                    id=str(item['id']).replace('flow:', ''),
                    name=item['name'],
                    description=item['description'],
                    steps=steps,
                    metadata=item.get('metadata', {}),
                    created_at=datetime.fromisoformat(item['created_at'].replace('Z', '')).replace(tzinfo=timezone.utc),
                    is_active=item.get('is_active', True)
                )
        return None

    async def create_execution(self, execution: FlowExecution) -> str:
        """Create a flow execution record."""
        query = """
        CREATE type::thing('flow_execution', $id) CONTENT {
            flow_id: $flow_id,
            user_id: $user_id,
            status: $status,
            current_step_index: $current_step_index,
            context: $context,
            results: $results,
            started_at: $started_at,
            ended_at: $ended_at
        };
        """
        params = {
            "id": execution.id,
            "flow_id": execution.flow_id,
            "user_id": execution.user_id,
            "status": execution.status,
            "current_step_index": execution.current_step_index,
            "context": execution.context,
            "results": execution.results,
            "started_at": execution.started_at.isoformat(),
            "ended_at": execution.ended_at.isoformat() if execution.ended_at else None
        }

        async with self.client.get_connection() as conn:
            await conn.query(query, params)
            return execution.id

    async def update_execution(self, execution: FlowExecution) -> None:
        """Update a flow execution status."""
        query = """
        UPDATE type::thing('flow_execution', $id) CONTENT {
            flow_id: $flow_id,
            user_id: $user_id,
            status: $status,
            current_step_index: $current_step_index,
            context: $context,
            results: $results,
            started_at: $started_at,
            ended_at: $ended_at
        };
        """
        # Reusing create params logic
        params = {
            "id": execution.id,
            "flow_id": execution.flow_id,
            "user_id": execution.user_id,
            "status": execution.status,
            "current_step_index": execution.current_step_index,
            "context": execution.context,
            "results": execution.results,
            "started_at": execution.started_at.isoformat(),
            "ended_at": execution.ended_at.isoformat() if execution.ended_at else None
        }

        async with self.client.get_connection() as conn:
            await conn.query(query, params)
