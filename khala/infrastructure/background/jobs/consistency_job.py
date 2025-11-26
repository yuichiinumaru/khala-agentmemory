"""Consistency check job for KHALA.

This job analyzes a specific memory against related memories to detect
logical contradictions or inconsistencies.
"""

import logging
import json
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from ....domain.memory.entities import Memory
from ....infrastructure.gemini.client import GeminiClient
from ....infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class ConsistencyJob:
    """Job to check for consistency between memories."""
    
    def __init__(self, db_client: SurrealDBClient, gemini_client: Optional[GeminiClient] = None):
        self.db_client = db_client
        self.gemini_client = gemini_client or GeminiClient()
        
    async def execute(self, job_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute consistency check on a memory.
        
        Args:
            job_payload: Dict containing 'memory_id'
            
        Returns:
            Dict with check results
        """
        memory_id = job_payload.get("memory_id")
        if not memory_id:
            raise ValueError("memory_id required in payload")
            
        # 1. Get target memory
        memory = await self.db_client.get_memory(memory_id)
        if not memory:
            raise ValueError(f"Memory {memory_id} not found")
            
        if not memory.embedding:
            logger.warning(f"Memory {memory_id} has no embedding, skipping consistency check")
            return {"status": "skipped", "reason": "no_embedding"}
            
        # 2. Find related memories using vector search
        # We exclude the memory itself and look for high similarity
        related_records = await self.db_client.search_memories_by_vector(
            embedding=memory.embedding,
            user_id=memory.user_id,
            top_k=5,
            min_similarity=0.7
        )
        
        # Filter out the memory itself
        related_memories = [
            await self.db_client.get_memory(r['id']) 
            for r in related_records 
            if r['id'] != memory.id
        ]
        
        # Filter out None values if get_memory failed
        related_memories = [m for m in related_memories if m]
        
        if not related_memories:
            return {"status": "passed", "reason": "no_related_memories"}
            
        # 3. Analyze for contradictions using Gemini
        contradictions = await self._analyze_contradictions(memory, related_memories)
        
        # 4. Update memory if contradictions found
        if contradictions:
            await self._update_memory_with_issues(memory, contradictions)
            
        return {
            "status": "completed",
            "contradictions_found": len(contradictions),
            "contradictions": contradictions,
            "related_memories_checked": len(related_memories)
        }
    
    async def _analyze_contradictions(self, target: Memory, related: List[Memory]) -> List[str]:
        """Use LLM to detect contradictions."""
        
        related_text = "\n".join([
            f"- [{m.id}] {m.content} (Confidence: {m.metadata.get('confidence', 'unknown')})"
            for m in related
        ])
        
        prompt = f"""
        Analyze the following new memory against existing memories for logical contradictions.
        
        NEW MEMORY:
        {target.content}
        
        EXISTING MEMORIES:
        {related_text}
        
        Task:
        Identify if the NEW MEMORY logically contradicts any of the EXISTING MEMORIES.
        Ignore minor differences in phrasing or detail. Focus on factual conflicts (e.g., "Sky is blue" vs "Sky is green").
        
        If there are contradictions, list them concisely. If none, return "NONE".
        
        Format:
        - Contradiction 1
        - Contradiction 2
        """
        
        try:
            response = await self.gemini_client.generate_text(
                prompt,
                model_id="gemini-2.0-flash",
                temperature=0.0
            )
            
            content = response.get("content", "").strip()
            
            if content == "NONE" or not content:
                return []
            
            # Parse list
            lines = [line.strip().lstrip('- ').strip() for line in content.split('\n') if line.strip()]
            return lines
            
        except Exception as e:
            logger.error(f"Gemini analysis failed: {e}")
            return []

    async def _update_memory_with_issues(self, memory: Memory, issues: List[str]):
        """Update memory verification issues."""
        current_issues = memory.verification_issues or []
        new_issues = list(set(current_issues + issues))
        
        # Update the memory object
        memory.verification_issues = new_issues
        memory.verification_score = 0.0
        memory.updated_at = datetime.now(timezone.utc)
        
        # Save full object
        await self.db_client.update_memory(memory)
