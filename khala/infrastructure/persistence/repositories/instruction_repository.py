from typing import List, Optional, Dict, Any
from khala.domain.instruction.repository import InstructionRepository
from khala.domain.instruction.entities import Instruction, InstructionType
from khala.infrastructure.surrealdb.client import SurrealDBClient
from datetime import datetime, timezone

class SurrealInstructionRepository(InstructionRepository):
    """
    SurrealDB implementation of InstructionRepository.
    """
    def __init__(self, client: SurrealDBClient):
        self.client = client
        self.table = "instruction"

    def _to_entity(self, data: Dict[str, Any]) -> Instruction:
        """Convert DB record to Instruction entity."""
        # Handle enum conversion
        itype = data.get("instruction_type", "system")
        if isinstance(itype, str):
            try:
                itype = InstructionType(itype)
            except ValueError:
                itype = InstructionType.SYSTEM

        return Instruction(
            id=data["id"],
            name=data.get("name", "Unknown"),
            content=data.get("content", ""),
            instruction_type=itype,
            version=data.get("version", "1.0.0"),
            variables=data.get("variables", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if isinstance(data.get("created_at"), str) else data.get("created_at"),
            updated_at=datetime.fromisoformat(data["updated_at"]) if isinstance(data.get("updated_at"), str) else data.get("updated_at"),
            is_active=data.get("is_active", True)
        )

    def _to_dict(self, instruction: Instruction) -> Dict[str, Any]:
        """Convert Instruction entity to DB record."""
        return {
            "id": instruction.id,
            "name": instruction.name,
            "content": instruction.content,
            "instruction_type": instruction.instruction_type.value,
            "version": instruction.version,
            "variables": instruction.variables,
            "tags": instruction.tags,
            "metadata": instruction.metadata,
            "created_at": instruction.created_at.isoformat(),
            "updated_at": instruction.updated_at.isoformat(),
            "is_active": instruction.is_active
        }

    async def create(self, instruction: Instruction) -> Instruction:
        data = self._to_dict(instruction)
        # Ensure ID format
        if not data["id"].startswith(f"{self.table}:"):
            data["id"] = f"{self.table}:{data['id']}"

        created = await self.client.create(self.table, data)
        return self._to_entity(created[0]) if created else instruction

    async def get_by_id(self, instruction_id: str) -> Optional[Instruction]:
        if not instruction_id.startswith(f"{self.table}:"):
            instruction_id = f"{self.table}:{instruction_id}"

        result = await self.client.select(instruction_id)
        return self._to_entity(result) if result else None

    async def get_by_name(self, name: str) -> Optional[Instruction]:
        # Using a select with where clause
        query = f"SELECT * FROM {self.table} WHERE name = $name LIMIT 1;"
        async with self.client.get_connection() as conn:
            result = await conn.query(query, {"name": name})
            if result and isinstance(result, list) and len(result) > 0 and result[0].get('result'):
                 items = result[0]['result']
                 if items:
                     return self._to_entity(items[0])
        return None

    async def search(self, query: str, limit: int = 10) -> List[Instruction]:
        # Simple contains search for now, could be improved with FTS
        sql = f"SELECT * FROM {self.table} WHERE content CONTAINS $query LIMIT $limit;"
        async with self.client.get_connection() as conn:
            result = await conn.query(sql, {"query": query, "limit": limit})
            if result and isinstance(result, list) and len(result) > 0 and result[0].get('result'):
                 return [self._to_entity(item) for item in result[0]['result']]
        return []

    async def get_by_type(self, instruction_type: InstructionType) -> List[Instruction]:
        sql = f"SELECT * FROM {self.table} WHERE instruction_type = $itype;"
        async with self.client.get_connection() as conn:
            result = await conn.query(sql, {"itype": instruction_type.value})
            if result and isinstance(result, list) and len(result) > 0 and result[0].get('result'):
                 return [self._to_entity(item) for item in result[0]['result']]
        return []

    async def update(self, instruction: Instruction) -> Instruction:
        data = self._to_dict(instruction)
        # Ensure updated_at is fresh
        data["updated_at"] = datetime.now(timezone.utc).isoformat()

        if not data["id"].startswith(f"{self.table}:"):
            data["id"] = f"{self.table}:{data['id']}"

        updated = await self.client.update(data["id"], data)
        return self._to_entity(updated) if updated else instruction

    async def delete(self, instruction_id: str) -> bool:
        if not instruction_id.startswith(f"{self.table}:"):
            instruction_id = f"{self.table}:{instruction_id}"

        await self.client.delete(instruction_id)
        return True
