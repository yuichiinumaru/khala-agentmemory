"""Service for orchestrating deterministic Flows (Strategy 116)."""

import logging
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from khala.domain.flow.entities import Flow, FlowExecution, FlowStep
from khala.infrastructure.persistence.flow_repository import FlowRepository

logger = logging.getLogger(__name__)

class FlowOrchestrator:
    """Orchestrator for executing deterministic flows."""

    def __init__(self, repository: FlowRepository):
        self.repository = repository

    async def register_flow(self, flow: Flow) -> str:
        """Register a new flow definition."""
        return await self.repository.save_flow(flow)

    async def start_flow(self, flow_id: str, user_id: str, initial_context: Dict[str, Any] = None) -> str:
        """Start a new execution of a flow."""
        flow = await self.repository.get_flow(flow_id)
        if not flow:
            raise ValueError(f"Flow {flow_id} not found")

        execution = FlowExecution(
            flow_id=flow_id,
            user_id=user_id,
            status="running",
            context=initial_context or {},
            started_at=datetime.now(timezone.utc)
        )

        await self.repository.create_execution(execution)

        # In a real system, we might trigger an async job here.
        # For this implementation, we'll return the ID and let the caller trigger 'advance'.
        return execution.id

    async def advance_flow(self, execution_id: str) -> str:
        """Advance the flow to the next step."""
        # Note: This is a simplified synchronous-like advancement.
        # In production, this would be an async job loop.

        # 1. Fetch execution (we need a get_execution method in repository, implementing simpler fetch here for now)
        # Using client directly via repository since get_execution wasn't in interface I made (oops)
        # Let's add get_execution to repository or use a custom query here.
        query = "SELECT * FROM type::thing('flow_execution', $id);"
        params = {"id": execution_id}

        execution_data = None
        async with self.repository.client.get_connection() as conn:
             resp = await conn.query(query, params)
             if resp and isinstance(resp, list) and len(resp) > 0:
                 item = resp[0]
                 if isinstance(item, dict) and 'result' in item:
                     item = item['result'][0] if item['result'] else None
                 execution_data = item

        if not execution_data:
            raise ValueError(f"Execution {execution_id} not found")

        # Reconstruct execution object (simplified)
        execution = FlowExecution(
            id=str(execution_data['id']).replace('flow_execution:', ''),
            flow_id=execution_data['flow_id'],
            user_id=execution_data['user_id'],
            status=execution_data['status'],
            current_step_index=execution_data['current_step_index'],
            context=execution_data.get('context', {}),
            results=execution_data.get('results', {}),
            started_at=datetime.fromisoformat(execution_data['started_at'].replace('Z', '')).replace(tzinfo=timezone.utc),
            ended_at=datetime.fromisoformat(execution_data['ended_at'].replace('Z', '')).replace(tzinfo=timezone.utc) if execution_data.get('ended_at') else None
        )

        flow = await self.repository.get_flow(execution.flow_id)
        if not flow:
             raise ValueError("Flow definition missing")

        if execution.status != "running":
            return execution.status

        if execution.current_step_index >= len(flow.steps):
            execution.status = "completed"
            execution.ended_at = datetime.now(timezone.utc)
            await self.repository.update_execution(execution)
            return "completed"

        current_step = flow.steps[execution.current_step_index]

        try:
            # Execute step logic
            result = await self._execute_step_tool(current_step, execution.context)

            # Update context/results
            execution.results[current_step.name] = result
            if isinstance(result, dict):
                execution.context.update(result) # Merge result into context if dict

            execution.current_step_index += 1

            if execution.current_step_index >= len(flow.steps):
                execution.status = "completed"
                execution.ended_at = datetime.now(timezone.utc)

            await self.repository.update_execution(execution)
            return execution.status

        except Exception as e:
            logger.error(f"Step failed: {e}")
            execution.status = "failed"
            execution.results[current_step.name] = {"error": str(e)}
            execution.ended_at = datetime.now(timezone.utc)
            await self.repository.update_execution(execution)
            raise

    async def _execute_step_tool(self, step: FlowStep, context: Dict[str, Any]) -> Any:
        """Execute the tool defined in the step."""
        # Placeholder for tool execution logic.
        # This would interface with MCP or local tool registry.
        logger.info(f"Executing tool {step.tool} with params {step.parameters} and context {context.keys()}")

        # Simulate success
        return {"status": "success", "output": f"Executed {step.tool}"}
