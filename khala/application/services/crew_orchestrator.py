"""Service for orchestrating Autonomous Crews (Strategy 116)."""

import logging
from typing import List, Optional, Dict, Any

from khala.domain.crew.entities import Crew, CrewTask, AgentMember
from khala.infrastructure.persistence.crew_repository import CrewRepository

logger = logging.getLogger(__name__)

class CrewOrchestrator:
    """Orchestrator for autonomous crews."""

    def __init__(self, repository: CrewRepository):
        self.repository = repository

    async def assemble_crew(self, crew: Crew) -> str:
        """Create/Assemble a new crew."""
        return await self.repository.save_crew(crew)

    async def assign_task(self, task: CrewTask) -> str:
        """Assign a task to a crew."""
        # Validate crew exists
        crew = await self.repository.get_crew(task.crew_id)
        if not crew:
            raise ValueError(f"Crew {task.crew_id} not found")

        # If no specific member assigned, Manager (Leader) should pick it up.
        # Logic for "Manager Agent" to route task would go here.
        # For now, we just persist the task in pending state.

        return await self.repository.create_task(task)

    async def get_pending_tasks(self, crew_id: str) -> List[CrewTask]:
        """Get pending tasks for a crew."""
        # Simple query helper not in repo, using client direct access or adding to repo.
        # Adding to repo is better but for speed I will use client query here.
        query = """
        SELECT * FROM crew_task
        WHERE crew_id = $crew_id AND status = 'pending';
        """
        params = {"crew_id": crew_id}

        tasks = []
        async with self.repository.client.get_connection() as conn:
            resp = await conn.query(query, params)
            if resp and isinstance(resp, list):
                 data = resp
                 if len(resp) > 0 and isinstance(resp[0], dict) and 'result' in resp[0]:
                     data = resp[0]['result']

                 for item in data:
                     tasks.append(CrewTask(
                         id=str(item['id']).replace('crew_task:', ''),
                         crew_id=item['crew_id'],
                         description=item['description'],
                         expected_outcome=item['expected_outcome'],
                         assigned_to_member=item.get('assigned_to_member'),
                         status=item['status'],
                         result=item.get('result')
                     ))
        return tasks

    async def update_task_status(self, task_id: str, status: str, result: Optional[str] = None) -> None:
        """Update task status."""
        # We need to fetch, update object, save.
        # Since I didn't add get_task to repo, I'll do a direct update query for efficiency.

        # Handle ID prefix
        if ":" in task_id:
            task_id = task_id.split(":")[1]

        query = """
        UPDATE type::thing('crew_task', $id)
        SET status = $status, result = $result;
        """
        params = {
            "id": task_id,
            "status": status,
            "result": result
        }

        async with self.repository.client.get_connection() as conn:
            await conn.query(query, params)
