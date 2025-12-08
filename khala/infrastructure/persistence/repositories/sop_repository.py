"""SurrealDB implementation of SOP Repository."""

import logging
from typing import List, Optional, Any
from datetime import datetime, timezone

from khala.domain.sop.entities import SOP, SOPStep
from khala.domain.sop.repository import SOPRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class SurrealSOPRepository(SOPRepository):
    """SurrealDB implementation for storing SOPs."""

    def __init__(self, client: SurrealDBClient):
        self.client = client
        self.table = "sop"

    def _to_entity(self, record: dict) -> SOP:
        """Convert DB record to SOP entity."""
        # Handle case where record is a list (SurrealDB quirk for single selects sometimes)
        if isinstance(record, list):
            if not record:
                raise ValueError("Cannot convert empty record list to SOP")
            record = record[0]

        steps = []
        for s in record.get("steps", []):
            steps.append(SOPStep(
                order=s.get("order", 0),
                description=s.get("description", ""),
                expected_output=s.get("expected_output", ""),
                required_tools=s.get("required_tools", []),
                required_skills=s.get("required_skills", []),
                estimated_time_minutes=s.get("estimated_time_minutes", 5)
            ))

        # Convert record ID to string if it's an object/RecordID
        record_id = str(record["id"])

        return SOP(
            id=record_id,
            title=record.get("title", ""),
            objective=record.get("objective", ""),
            steps=steps,
            triggers=record.get("triggers", []),
            owner_role=record.get("owner_role", "worker"),
            tags=record.get("tags", []),
            metadata=record.get("metadata", {}),
            version=record.get("version", "1.0.0"),
            is_active=record.get("is_active", True),
            created_at=self.client._parse_dt(record.get("created_at")),
            updated_at=self.client._parse_dt(record.get("updated_at"))
        )

    async def create(self, sop: SOP) -> str:
        """Create a new SOP."""
        data = {
            "title": sop.title,
            "objective": sop.objective,
            "steps": [s.__dict__ for s in sop.steps],
            "triggers": sop.triggers,
            "owner_role": sop.owner_role,
            "tags": sop.tags,
            "metadata": sop.metadata,
            "version": sop.version,
            "is_active": sop.is_active,
            "created_at": sop.created_at,
            "updated_at": sop.updated_at
        }

        async with self.client.get_connection() as conn:
            if sop.id:
                record_id = sop.id if ":" in sop.id else f"{self.table}:{sop.id}"
                result = await conn.create(record_id, data)
            else:
                result = await conn.create(self.table, data)

            if isinstance(result, list) and result:
                return str(result[0]["id"])
            elif isinstance(result, dict):
                 return str(result["id"])

            raise RuntimeError(f"Failed to create SOP, unexpected result: {result}")

    async def get(self, sop_id: str) -> Optional[SOP]:
        """Get an SOP by ID."""
        record_id = sop_id if ":" in sop_id else f"{self.table}:{sop_id}"
        async with self.client.get_connection() as conn:
            result = await conn.select(record_id)
            # Result could be the dict itself or a list containing the dict
            if result:
                return self._to_entity(result)
            return None

    async def update(self, sop: SOP) -> None:
        """Update an existing SOP."""
        record_id = sop.id if ":" in sop.id else f"{self.table}:{sop.id}"
        data = {
            "title": sop.title,
            "objective": sop.objective,
            "steps": [s.__dict__ for s in sop.steps],
            "triggers": sop.triggers,
            "owner_role": sop.owner_role,
            "tags": sop.tags,
            "metadata": sop.metadata,
            "version": sop.version,
            "is_active": sop.is_active,
            "updated_at": datetime.now(timezone.utc)
        }
        async with self.client.get_connection() as conn:
            await conn.update(record_id, data)

    async def list_active(self) -> List[SOP]:
        """List all active SOPs."""
        query = f"SELECT * FROM {self.table} WHERE is_active = true"
        async with self.client.get_connection() as conn:
            results = await conn.query(query)
            if results and results[0]["status"] == "OK":
                return [self._to_entity(r) for r in results[0]["result"]]
            return []

    async def search_by_trigger(self, trigger: str) -> List[SOP]:
        """Search SOPs by trigger (exact match in array)."""
        query = f"SELECT * FROM {self.table} WHERE is_active = true AND triggers CONTAINS $trigger"
        async with self.client.get_connection() as conn:
            results = await conn.query(query, {"trigger": trigger})
            if results and results[0]["status"] == "OK":
                return [self._to_entity(r) for r in results[0]["result"]]
            return []

    async def search_by_tag(self, tag: str) -> List[SOP]:
        """Search SOPs by tag."""
        query = f"SELECT * FROM {self.table} WHERE is_active = true AND tags CONTAINS $tag"
        async with self.client.get_connection() as conn:
            results = await conn.query(query, {"tag": tag})
            if results and results[0]["status"] == "OK":
                return [self._to_entity(r) for r in results[0]["result"]]
            return []
