"""Application service for managing instructions (Von Neumann Pattern).

This service implements the strict separation of Instructions (Program) and Data (Memories).
"""

import logging
from dataclasses import asdict
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone

from khala.domain.instruction.entities import Instruction, InstructionType, InstructionSet
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class InstructionService:
    """Service for managing system instructions and prompts."""

    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client

    async def create_instruction(self, instruction: Instruction) -> Instruction:
        """Create or update an instruction."""
        data = asdict(instruction)

        # Handle Enum serialization
        if isinstance(data['instruction_type'], InstructionType):
            data['instruction_type'] = data['instruction_type'].value

        record_id = f"instruction:{instruction.id}"
        id_part = instruction.id

        upsert_query = """
        UPDATE type::thing('instruction', $id) CONTENT $data;
        """

        # Serialize datetimes
        data['created_at'] = data['created_at'].isoformat()
        data['updated_at'] = data['updated_at'].isoformat()

        try:
            async with self.db_client.get_connection() as conn:
                await conn.query(upsert_query, {"id": id_part, "data": data})
                logger.info(f"Registered Instruction: {instruction.name} ({instruction.id})")
                return instruction
        except Exception as e:
            logger.error(f"Error creating instruction {instruction.id}: {e}")
            raise

    async def get_instruction(self, instruction_id: str) -> Optional[Instruction]:
        """Retrieve an instruction by ID."""
        id_part = instruction_id.split(':')[1] if ':' in instruction_id else instruction_id

        query = "SELECT * FROM type::thing('instruction', $id);"

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, {"id": id_part})
                if result:
                    return self._map_to_instruction(result[0])
                return None
        except Exception as e:
            logger.error(f"Error getting instruction {instruction_id}: {e}")
            return None

    async def get_instructions_by_type(self, instruction_type: InstructionType) -> List[Instruction]:
        """Retrieve all active instructions of a specific type."""
        query = """
        SELECT * FROM instruction
        WHERE instruction_type = $type AND is_active = true;
        """

        try:
            async with self.db_client.get_connection() as conn:
                results = await conn.query(query, {"type": instruction_type.value})
                return [self._map_to_instruction(data) for data in results]
        except Exception as e:
            logger.error(f"Error getting instructions by type {instruction_type}: {e}")
            return []

    async def get_active_instructions(self, tags: List[str] = None) -> List[Instruction]:
        """Retrieve active instructions, optionally filtering by tags."""
        if tags:
            query = """
            SELECT * FROM instruction
            WHERE is_active = true AND tags CONTAINSANY $tags;
            """
            params = {"tags": tags}
        else:
            query = """
            SELECT * FROM instruction
            WHERE is_active = true;
            """
            params = {}

        try:
            async with self.db_client.get_connection() as conn:
                results = await conn.query(query, params)
                return [self._map_to_instruction(data) for data in results]
        except Exception as e:
            logger.error(f"Error getting active instructions: {e}")
            return []

    def _map_to_instruction(self, data: Dict[str, Any]) -> Instruction:
        """Map database result to Instruction entity."""
        inst_id = data.get("id", "")
        if inst_id.startswith("instruction:"):
            inst_id = inst_id.split(":")[1]

        return Instruction(
            id=inst_id,
            name=data.get("name"),
            content=data.get("content"),
            instruction_type=InstructionType(data.get("instruction_type")),
            version=data.get("version", "1.0.0"),
            variables=data.get("variables", []),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=self._parse_datetime(data.get("created_at")),
            updated_at=self._parse_datetime(data.get("updated_at")),
            is_active=data.get("is_active", True)
        )

    def _parse_datetime(self, dt_str: Any) -> datetime:
        """Helper to parse datetime strings."""
        if isinstance(dt_str, datetime):
            return dt_str
        if isinstance(dt_str, str):
            try:
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            except ValueError:
                return datetime.now(timezone.utc)
        return datetime.now(timezone.utc)
