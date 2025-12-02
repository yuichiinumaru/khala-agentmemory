import uuid
import logging
from typing import List, Dict, Any, Optional

from ...domain.crew.entities import Crew, CrewMember, CrewRole
from ...domain.agent.entities import AgentProfile, AgentRole, AgentStatus

logger = logging.getLogger(__name__)

class CrewOrchestrator:
    def __init__(self):
        self.crews: Dict[str, Crew] = {}

    def create_crew(self, name: str, mission: str, members: List[AgentProfile]) -> Crew:
        crew = Crew(
            id=str(uuid.uuid4()),
            name=name,
            members={},
            mission=mission
        )

        for agent in members:
            # First member is leader by default if manager
            role = CrewRole.MEMBER
            if not crew.leader_id and agent.role == AgentRole.MANAGER:
                role = CrewRole.LEADER

            member = CrewMember(
                agent_id=agent.id,
                role=role,
                profile=agent
            )
            crew.add_member(member)

        self.crews[crew.id] = crew
        return crew

    async def delegate_task(self, crew_id: str, task: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Delegates a high-level task to the crew leader.
        The leader (simulated or real) breaks it down.
        """
        crew = self.crews.get(crew_id)
        if not crew:
            raise ValueError(f"Crew {crew_id} not found")

        leader = crew.get_leader()
        if not leader:
            raise ValueError(f"Crew {crew_id} has no leader")

        logger.info(f"Delegating task to crew {crew.name} via leader {leader.profile.name}")

        # Task 117: Hierarchical Delegation Logic
        # In a real system, we would ask the LLM (Leader) to decompose the task.
        # Here we will simulate decomposition or use a simplistic heuristic if no LLM is connected.

        subtasks = self._decompose_task(task, crew)
        results = []

        for subtask in subtasks:
            assigned_member = self._assign_task(subtask, crew)
            if assigned_member:
                logger.info(f"Assigned '{subtask['description']}' to {assigned_member.profile.name}")
                # Execute logic (simulated)
                results.append({
                    "task": subtask['description'],
                    "assignee": assigned_member.profile.name,
                    "status": "completed",
                    "result": f"Result for {subtask['description']}"
                })
            else:
                results.append({
                    "task": subtask['description'],
                    "status": "failed",
                    "error": "No available member"
                })

        return {
            "crew_id": crew.id,
            "task": task,
            "results": results
        }

    def _decompose_task(self, task: str, crew: Crew) -> List[Dict[str, Any]]:
        # Placeholder for LLM-based decomposition
        # Returns a list of subtasks
        return [
            {"description": f"Analyze requirements for {task}", "required_role": "analyst"},
            {"description": f"Execute core logic for {task}", "required_role": "worker"},
            {"description": f"Verify output for {task}", "required_role": "reviewer"}
        ]

    def _assign_task(self, subtask: Dict[str, Any], crew: Crew) -> Optional[CrewMember]:
        # Simple matching strategy
        required_role = subtask.get("required_role")

        # 1. Look for a specialist member (non-leader)
        for member in crew.members.values():
            if member.role != CrewRole.LEADER and required_role in member.profile.capabilities:
                return member

        # 2. Look for the leader if they can do it (or as fallback if we want leader to pick up slack)
        for member in crew.members.values():
            if member.role == CrewRole.LEADER:
                 return member

        # 3. Fallback to any member
        if crew.members:
            return list(crew.members.values())[0]
        return None
