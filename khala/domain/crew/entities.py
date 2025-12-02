from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from enum import Enum
from ..agent.entities import AgentProfile, AgentRole

class CrewRole(Enum):
    LEADER = "leader"
    MEMBER = "member"

@dataclass
class CrewMember:
    agent_id: str
    role: CrewRole
    profile: AgentProfile
    responsibilities: List[str] = field(default_factory=list)

@dataclass
class Crew:
    id: str
    name: str
    members: Dict[str, CrewMember]  # agent_id -> CrewMember
    mission: str
    leader_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def add_member(self, member: CrewMember):
        self.members[member.agent_id] = member
        if member.role == CrewRole.LEADER:
            self.leader_id = member.agent_id

    def get_leader(self) -> Optional[CrewMember]:
        if self.leader_id:
            return self.members.get(self.leader_id)
        return None
