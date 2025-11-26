"""Domain services for SOP management."""

import logging
from typing import List, Dict, Optional

from .entities import SOP, SOPStep

logger = logging.getLogger(__name__)

class SOPRegistry:
    """Service for managing Standard Operating Procedures."""
    
    def __init__(self):
        self._sops: Dict[str, SOP] = {}
        
    def register_sop(self, sop: SOP) -> None:
        """Register a new SOP."""
        self._sops[sop.id] = sop
        logger.info(f"Registered SOP: {sop.title} ({sop.id})")
        
    def get_sop(self, sop_id: str) -> Optional[SOP]:
        """Get an SOP by ID."""
        return self._sops.get(sop_id)
        
    def find_sops_by_trigger(self, trigger_text: str) -> List[SOP]:
        """Find SOPs that match a trigger text."""
        matches = []
        trigger_lower = trigger_text.lower()
        for sop in self._sops.values():
            if not sop.is_active:
                continue
            for trig in sop.triggers:
                if trig.lower() in trigger_lower:
                    matches.append(sop)
                    break
        return matches
        
    def find_sops_by_tag(self, tag: str) -> List[SOP]:
        """Find SOPs by tag."""
        return [
            sop for sop in self._sops.values() 
            if sop.is_active and tag in sop.tags
        ]
