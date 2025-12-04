from typing import List, Dict, Any, Optional
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
import uuid
import json

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.domain.instruction.repository import InstructionRepository
from khala.domain.instruction.entities import Instruction, InstructionType

logger = logging.getLogger(__name__)

@dataclass
class SOP:
    """Standard Operating Procedure entity."""
    id: str
    name: str
    description: str
    steps: List[str]
    required_role: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)

class SOPService:
    """
    Service for managing Standard Operating Procedures (SOPs).
    Strategy 46: Standard Operating Procedures.
    """
    def __init__(self, db_client: SurrealDBClient, instruction_repo: InstructionRepository):
        self.db_client = db_client
        self.instruction_repo = instruction_repo
        self.table = "sop"

    async def create_sop(self, name: str, description: str, steps: List[str], role: Optional[str] = None) -> SOP:
        """Create a new SOP."""
        sop_id = f"{self.table}:{uuid.uuid4()}"
        sop = SOP(
            id=sop_id,
            name=name,
            description=description,
            steps=steps,
            required_role=role
        )

        data = {
            "id": sop.id,
            "name": sop.name,
            "description": sop.description,
            "steps": sop.steps,
            "required_role": sop.required_role,
            "created_at": sop.created_at.isoformat(),
            "metadata": sop.metadata
        }

        await self.db_client.create(self.table, data)
        return sop

    async def get_sop(self, sop_id: str) -> Optional[SOP]:
        """Retrieve an SOP by ID."""
        if not sop_id.startswith(f"{self.table}:"):
            sop_id = f"{self.table}:{sop_id}"

        result = await self.db_client.select(sop_id)
        if result:
            return SOP(
                id=result["id"],
                name=result["name"],
                description=result["description"],
                steps=result["steps"],
                required_role=result.get("required_role"),
                created_at=datetime.fromisoformat(result["created_at"]) if isinstance(result.get("created_at"), str) else result.get("created_at"),
                metadata=result.get("metadata", {})
            )
        return None

    async def list_sops(self) -> List[SOP]:
        """List all SOPs."""
        result = await self.db_client.select(self.table)
        sops = []
        if isinstance(result, list):
            for r in result:
                sops.append(SOP(
                    id=r["id"],
                    name=r["name"],
                    description=r["description"],
                    steps=r["steps"],
                    required_role=r.get("required_role"),
                    created_at=datetime.fromisoformat(r["created_at"]) if isinstance(r.get("created_at"), str) else r.get("created_at"),
                    metadata=r.get("metadata", {})
                ))
        return sops

    async def execute_sop(self, sop_id: str, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Simulate execution of an SOP.
        In a real agent system, this would orchestrate agent actions.
        Here we return a plan/trace.
        """
        sop = await self.get_sop(sop_id)
        if not sop:
            raise ValueError(f"SOP {sop_id} not found")

        execution_trace = {
            "sop_id": sop.id,
            "sop_name": sop.name,
            "started_at": datetime.now(timezone.utc).isoformat(),
            "steps_executed": [],
            "status": "completed"
        }

        # Logic to "execute" or guide an agent through steps
        for i, step in enumerate(sop.steps):
            # In a real implementation, this might call an agent or tool
            execution_trace["steps_executed"].append({
                "step_index": i,
                "instruction": step,
                "status": "simulated_success"
            })

        return execution_trace
