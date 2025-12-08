"""Domain services for SOP management."""

import logging
from typing import List, Optional

from .entities import SOP
from .repository import SOPRepository

logger = logging.getLogger(__name__)

class SOPRegistry:
    """Service for managing Standard Operating Procedures."""
    
    def __init__(self, repository: SOPRepository):
        self.repository = repository
        
    async def register_sop(self, sop: SOP) -> str:
        """Register a new SOP."""
        sop_id = await self.repository.create(sop)
        logger.info(f"Registered SOP: {sop.title} ({sop_id})")
        return sop_id
        
    async def get_sop(self, sop_id: str) -> Optional[SOP]:
        """Get an SOP by ID."""
        return await self.repository.get(sop_id)
        
    async def find_sops_by_trigger(self, trigger_text: str) -> List[SOP]:
        """Find SOPs that match a trigger text."""
        # Fix Regression: Use client-side filtering to support natural language matching
        # "triggers CONTAINS $trigger" only matches exact strings in the array.
        # We want: if any trigger word in SOP.triggers is IN the user's trigger_text.

        all_sops = await self.repository.list_active()
        matches = []
        trigger_lower = trigger_text.lower()

        for sop in all_sops:
            for trig in sop.triggers:
                # Original logic: check if the trigger phrase is inside the user text
                if trig.lower() in trigger_lower:
                    matches.append(sop)
                    break

        return matches
        
    async def find_sops_by_tag(self, tag: str) -> List[SOP]:
        """Find SOPs by tag."""
        return await self.repository.search_by_tag(tag)
