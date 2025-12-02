"""SurrealDB implementation of InstructionRepository."""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from khala.domain.instruction.entities import Instruction, InstructionSet, InstructionType
from khala.domain.instruction.repository import InstructionRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class SurrealDBInstructionRepository(InstructionRepository):
    """
    Repository for storing instructions in SurrealDB.
    """

    def __init__(self, client: SurrealDBClient):
        self.client = client
        self.table_instruction = "instruction"
        self.table_set = "instruction_set"

    def _to_entity(self, data: Dict[str, Any]) -> Instruction:
        """Convert DB record to Instruction entity."""
        # Handle datetime fields which might be strings from DB
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

        # Ensure ID format
        id_val = data.get("id", "")
        if ":" in id_val:
            id_val = id_val.split(":")[1]

        return Instruction(
            id=id_val,
            name=data.get("name", ""),
            content=data.get("content", ""),
            instruction_type=InstructionType(data.get("instruction_type", "system")),
            version=data.get("version", "1.0.0"),
            variables=data.get("variables", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc),
            is_active=data.get("is_active", True)
        )

    def _to_set_entity(self, data: Dict[str, Any]) -> InstructionSet:
        """Convert DB record to InstructionSet entity."""
        created_at = data.get("created_at")
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))

        updated_at = data.get("updated_at")
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))

        id_val = data.get("id", "")
        if ":" in id_val:
            id_val = id_val.split(":")[1]

        # Handle instructions list which might be records or IDs
        instructions = []
        raw_instructions = data.get("instructions", [])
        for item in raw_instructions:
            if isinstance(item, dict):
                instructions.append(self._to_entity(item))
            # Note: If it's just an ID string, we can't fully reconstruct it here without fetching.
            # For simplicity, we assume we get the expanded objects (FETCH instructions).

        return InstructionSet(
            id=id_val,
            name=data.get("name", ""),
            description=data.get("description", ""),
            instructions=instructions,
            target_agent_role=data.get("target_agent_role"),
            created_at=created_at or datetime.now(timezone.utc),
            updated_at=updated_at or datetime.now(timezone.utc)
        )

    def _to_record(self, instruction: Instruction) -> Dict[str, Any]:
        """Convert Instruction entity to DB record."""
        return {
            "id": f"{self.table_instruction}:{instruction.id}",
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

    def _to_set_record(self, instruction_set: InstructionSet) -> Dict[str, Any]:
        """Convert InstructionSet entity to DB record."""
        return {
            "id": f"{self.table_set}:{instruction_set.id}",
            "name": instruction_set.name,
            "description": instruction_set.description,
            "instructions": [f"{self.table_instruction}:{i.id}" for i in instruction_set.instructions],
            "target_agent_role": instruction_set.target_agent_role,
            "created_at": instruction_set.created_at.isoformat(),
            "updated_at": instruction_set.updated_at.isoformat()
        }

    async def create_instruction(self, instruction: Instruction) -> Instruction:
        """Create a new instruction."""
        record = self._to_record(instruction)
        # Use create with specific ID
        query = f"CREATE {record['id']} CONTENT $data;"

        async with self.client.get_connection() as conn:
            result = await conn.query(query, {"data": record})
            if result and result[0]['result']:
                return self._to_entity(result[0]['result'][0])
            raise Exception("Failed to create instruction")

    async def get_instruction(self, instruction_id: str) -> Optional[Instruction]:
        """Retrieve an instruction by ID."""
        if ":" not in instruction_id:
            instruction_id = f"{self.table_instruction}:{instruction_id}"

        async with self.client.get_connection() as conn:
            result = await conn.select(instruction_id)
            if result:
                return self._to_entity(result)
            return None

    async def get_instruction_by_name(self, name: str, version: Optional[str] = None) -> Optional[Instruction]:
        """Retrieve an instruction by name and optional version."""
        query = f"SELECT * FROM {self.table_instruction} WHERE name = $name"
        params = {"name": name}

        if version:
            query += " AND version = $version"
            params["version"] = version
        else:
            # If no version specified, get the latest active one (by created_at desc)
            query += " AND is_active = true ORDER BY created_at DESC LIMIT 1"

        async with self.client.get_connection() as conn:
            result = await conn.query(query, params)
            if result and result[0]['result']:
                return self._to_entity(result[0]['result'][0])
            return None

    async def list_instructions(self, instruction_type: Optional[InstructionType] = None, tags: Optional[List[str]] = None) -> List[Instruction]:
        """List instructions, optionally filtering by type or tags."""
        query = f"SELECT * FROM {self.table_instruction} WHERE is_active = true"
        params = {}

        if instruction_type:
            query += " AND instruction_type = $type"
            params["type"] = instruction_type.value

        if tags:
            # Check if tags array contains ANY of the provided tags
            query += " AND tags CONTAINSANY $tags"
            params["tags"] = tags

        query += " ORDER BY created_at DESC;"

        async with self.client.get_connection() as conn:
            result = await conn.query(query, params)
            if result and result[0]['result']:
                return [self._to_entity(r) for r in result[0]['result']]
            return []

    async def update_instruction(self, instruction: Instruction) -> Instruction:
        """Update an existing instruction."""
        record = self._to_record(instruction)
        # We don't want to overwrite created_at
        del record['created_at']
        record['updated_at'] = datetime.now(timezone.utc).isoformat()

        async with self.client.get_connection() as conn:
            result = await conn.update(record['id'], record)
            if result:
                return self._to_entity(result)
            raise Exception(f"Instruction {instruction.id} not found")

    async def delete_instruction(self, instruction_id: str) -> bool:
        """Delete an instruction."""
        if ":" not in instruction_id:
            instruction_id = f"{self.table_instruction}:{instruction_id}"

        async with self.client.get_connection() as conn:
            await conn.delete(instruction_id)
            return True

    async def create_instruction_set(self, instruction_set: InstructionSet) -> InstructionSet:
        """Create a new instruction set."""
        record = self._to_set_record(instruction_set)
        query = f"CREATE {record['id']} CONTENT $data;"

        async with self.client.get_connection() as conn:
            result = await conn.query(query, {"data": record})
            if result and result[0]['result']:
                # We need to re-fetch with FETCH to get full instruction objects
                fetch_query = f"SELECT * FROM {record['id']} FETCH instructions;"
                fetched = await conn.query(fetch_query)
                if fetched and fetched[0]['result']:
                     return self._to_set_entity(fetched[0]['result'][0])
            raise Exception("Failed to create instruction set")

    async def get_instruction_set(self, set_id: str) -> Optional[InstructionSet]:
        """Retrieve an instruction set by ID."""
        if ":" not in set_id:
            set_id = f"{self.table_set}:{set_id}"

        query = f"SELECT * FROM {set_id} FETCH instructions;"

        async with self.client.get_connection() as conn:
            result = await conn.query(query)
            if result and result[0]['result']:
                return self._to_set_entity(result[0]['result'][0])
            return None

    async def get_instruction_set_by_name(self, name: str) -> Optional[InstructionSet]:
        """Retrieve an instruction set by name."""
        query = f"SELECT * FROM {self.table_set} WHERE name = $name FETCH instructions LIMIT 1;"

        async with self.client.get_connection() as conn:
            result = await conn.query(query, {"name": name})
            if result and result[0]['result']:
                return self._to_set_entity(result[0]['result'][0])
            return None
