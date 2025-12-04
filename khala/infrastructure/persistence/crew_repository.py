"""Repository for Crew entities (Strategy 116)."""

from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from dataclasses import asdict

from khala.domain.crew.entities import Crew, CrewTask, AgentMember, CrewRole
from khala.infrastructure.surrealdb.client import SurrealDBClient

class CrewRepository:
    def __init__(self, client: SurrealDBClient):
        self.client = client

    async def save_crew(self, crew: Crew) -> str:
        """Save a crew definition."""
        # Serialize members (enum handling)
        members_data = []
        for member in crew.members:
            m_dict = asdict(member)
            m_dict['role'] = member.role.value
            members_data.append(m_dict)

        query = """
        CREATE type::thing('crew', $id) CONTENT {
            name: $name,
            objective: $objective,
            members: $members,
            manager_agent_id: $manager_agent_id,
            memory_context_id: $memory_context_id,
            status: $status,
            created_at: $created_at
        };
        """
        params = {
            "id": crew.id,
            "name": crew.name,
            "objective": crew.objective,
            "members": members_data,
            "manager_agent_id": crew.manager_agent_id,
            "memory_context_id": crew.memory_context_id,
            "status": crew.status,
            "created_at": crew.created_at.isoformat()
        }

        async with self.client.get_connection() as conn:
            await conn.query(query, params)
            return crew.id

    async def update_crew(self, crew: Crew) -> None:
        """Update a crew definition."""
        # Serialize members (enum handling)
        members_data = []
        for member in crew.members:
            m_dict = asdict(member)
            m_dict['role'] = member.role.value
            members_data.append(m_dict)

        query = """
        UPDATE type::thing('crew', $id) CONTENT {
            name: $name,
            objective: $objective,
            members: $members,
            manager_agent_id: $manager_agent_id,
            memory_context_id: $memory_context_id,
            status: $status,
            created_at: $created_at
        };
        """
        params = {
            "id": crew.id,
            "name": crew.name,
            "objective": crew.objective,
            "members": members_data,
            "manager_agent_id": crew.manager_agent_id,
            "memory_context_id": crew.memory_context_id,
            "status": crew.status,
            "created_at": crew.created_at.isoformat()
        }

        async with self.client.get_connection() as conn:
            await conn.query(query, params)

    async def get_crew(self, crew_id: str) -> Optional[Crew]:
        """Get a crew by ID."""
        query = "SELECT * FROM type::thing('crew', $id);"
        params = {"id": crew_id}

        async with self.client.get_connection() as conn:
            response = await conn.query(query, params)
            if response and isinstance(response, list) and len(response) > 0:
                item = response[0]
                if isinstance(item, dict) and 'result' in item:
                    item = item['result'][0] if item['result'] else None

                if not item:
                    return None

                # Reconstruct Crew object
                members = []
                for m_data in item.get('members', []):
                    # Convert role string back to Enum
                    m_data['role'] = CrewRole(m_data['role'])
                    members.append(AgentMember(**m_data))

                return Crew(
                    id=str(item['id']).replace('crew:', ''),
                    name=item['name'],
                    objective=item['objective'],
                    members=members,
                    manager_agent_id=item.get('manager_agent_id'),
                    memory_context_id=item.get('memory_context_id'),
                    status=item.get('status', 'active'),
                    created_at=datetime.fromisoformat(item['created_at'].replace('Z', '')).replace(tzinfo=timezone.utc)
                )
        return None

    async def create_task(self, task: CrewTask) -> str:
        """Create a crew task."""
        query = """
        CREATE type::thing('crew_task', $id) CONTENT {
            crew_id: $crew_id,
            description: $description,
            expected_outcome: $expected_outcome,
            assigned_to_member: $assigned_to_member,
            status: $status,
            result: $result,
            created_at: time::now()
        };
        """
        params = {
            "id": task.id,
            "crew_id": task.crew_id,
            "description": task.description,
            "expected_outcome": task.expected_outcome,
            "assigned_to_member": task.assigned_to_member,
            "status": task.status,
            "result": task.result
        }

        async with self.client.get_connection() as conn:
            await conn.query(query, params)
            return task.id

    async def update_task(self, task: CrewTask) -> None:
        """Update a crew task."""
        query = """
        UPDATE type::thing('crew_task', $id) CONTENT {
            crew_id: $crew_id,
            description: $description,
            expected_outcome: $expected_outcome,
            assigned_to_member: $assigned_to_member,
            status: $status,
            result: $result
        };
        """
        params = {
            "id": task.id,
            "crew_id": task.crew_id,
            "description": task.description,
            "expected_outcome": task.expected_outcome,
            "assigned_to_member": task.assigned_to_member,
            "status": task.status,
            "result": task.result
        }

        async with self.client.get_connection() as conn:
            await conn.query(query, params)
