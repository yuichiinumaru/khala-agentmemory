"""Domain services for SOP management."""

import logging
import json
import glob
import os
from dataclasses import asdict
from datetime import datetime, timezone
from typing import List, Dict, Optional, Any

from khala.infrastructure.surrealdb.client import SurrealDBClient
from .entities import SOP, SOPStep

logger = logging.getLogger(__name__)

class SOPRegistry:
    """Service for managing Standard Operating Procedures."""
    
    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client
        
    async def register_sop(self, sop: SOP) -> SOP:
        """Register a new SOP in the database."""
        # Convert to dict for storage
        data = asdict(sop)
        
        # Ensure ID format for SurrealDB (if not already handled)
        # Note: In SurrealDB v2, record IDs are typically table:id
        if not data['id'].startswith('sop:'):
             record_id = f"sop:{data['id']}"
        else:
             record_id = data['id']

        # Remove id from data to let SurrealDB handle it (or keep it if we want to force it)
        # But we need to make sure we use the same ID logic

        query = """
        CREATE type::thing('sop', $id) CONTENT $data;
        """

        # Strip the prefix for the $id parameter if we use type::thing
        id_part = record_id.split(':')[1] if ':' in record_id else record_id

        try:
            async with self.db_client.get_connection() as conn:
                 # Check if exists first to avoid duplicate errors or decide to update
                 # For now, we'll try to create.
                 # If we want upsert behavior:
                 upsert_query = """
                 UPDATE type::thing('sop', $id) CONTENT $data;
                 """

                 # Handling datetimes for serialization
                 data['created_at'] = data['created_at'].isoformat()
                 data['updated_at'] = data['updated_at'].isoformat()

                 result = await conn.query(upsert_query, {"id": id_part, "data": data})
                 logger.info(f"Registered SOP: {sop.title} ({sop.id})")
                 return sop
        except Exception as e:
            logger.error(f"Error registering SOP {sop.id}: {e}")
            raise

    async def get_sop(self, sop_id: str) -> Optional[SOP]:
        """Get an SOP by ID."""
        # Ensure ID format
        id_part = sop_id.split(':')[1] if ':' in sop_id else sop_id
        
        query = "SELECT * FROM type::thing('sop', $id);"

        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, {"id": id_part})
                if result:
                    data = result[0]
                    return self._map_to_sop(data)
                return None
        except Exception as e:
            logger.error(f"Error getting SOP {sop_id}: {e}")
            return None

    async def find_sops_by_trigger(self, trigger_text: str) -> List[SOP]:
        """Find SOPs that match a trigger text."""
        # This is a simple implementation. In production, we might want to use
        # full-text search or vector similarity if triggers are complex.
        # For now, we can fetch active SOPs and filter in memory or use CONTAINS.
        # Given SurrealDB capabilities, we can try to find if any trigger is contained in the text.

        # However, the requirement is "trigger matches text".
        # Usually it means if the user says "deploy to prod", and we have a trigger "deploy", it matches.

        # Let's fetch all active SOPs and check triggers in Python for flexibility
        # unless we have a massive number of SOPs.

        query = "SELECT * FROM sop WHERE is_active = true;"

        matches = []
        trigger_lower = trigger_text.lower()
        
        try:
            async with self.db_client.get_connection() as conn:
                results = await conn.query(query)
                for data in results:
                    sop = self._map_to_sop(data)
                    for trig in sop.triggers:
                        if trig.lower() in trigger_lower:
                            matches.append(sop)
                            break
            return matches
        except Exception as e:
            logger.error(f"Error finding SOPs by trigger: {e}")
            return []

    async def find_sops_by_tag(self, tag: str) -> List[SOP]:
        """Find SOPs by tag."""
        query = "SELECT * FROM sop WHERE is_active = true AND $tag IN tags;"

        try:
            async with self.db_client.get_connection() as conn:
                results = await conn.query(query, {"tag": tag})
                return [self._map_to_sop(data) for data in results]
        except Exception as e:
            logger.error(f"Error finding SOPs by tag: {e}")
            return []

    async def ingest_from_directory(self, directory_path: str = "docs/sops/") -> int:
        """Ingest SOPs from JSON files in a directory."""
        count = 0
        search_path = os.path.join(directory_path, "*.json")
        for filepath in glob.glob(search_path):
            try:
                with open(filepath, 'r') as f:
                    data = json.load(f)

                # Convert steps to SOPStep objects
                steps = []
                for step_data in data.get("steps", []):
                    steps.append(SOPStep(**step_data))

                sop = SOP(
                    id=data.get("id"),
                    title=data.get("title"),
                    objective=data.get("objective"),
                    steps=steps,
                    triggers=data.get("triggers", []),
                    owner_role=data.get("owner_role", "worker"),
                    tags=data.get("tags", []),
                    metadata=data.get("metadata", {}),
                    version=data.get("version", "1.0.0"),
                    is_active=data.get("is_active", True)
                )

                await self.register_sop(sop)
                count += 1
            except Exception as e:
                logger.error(f"Error ingesting SOP from {filepath}: {e}")

        return count

    def _map_to_sop(self, data: Dict[str, Any]) -> SOP:
        """Map database result to SOP entity."""
        # Parse steps back to objects
        steps = []
        for step_data in data.get("steps", []):
            steps.append(SOPStep(**step_data))

        # Handle ID (strip sop:)
        sop_id = data.get("id", "")
        if sop_id.startswith("sop:"):
            sop_id = sop_id.split(":")[1]

        return SOP(
            id=sop_id,
            title=data.get("title"),
            objective=data.get("objective"),
            steps=steps,
            triggers=data.get("triggers", []),
            owner_role=data.get("owner_role", "worker"),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            version=data.get("version", "1.0.0"),
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
                return datetime.now(timezone.utc) # Fallback
        return datetime.now(timezone.utc)
