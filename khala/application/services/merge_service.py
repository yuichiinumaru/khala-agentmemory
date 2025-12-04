"""Merge Service for Version Control (Module 15).

This service implements Strategy 158: Merge Conflict Resolution.
"""

from typing import List, Dict, Any, Optional, Tuple
import logging
from datetime import datetime

from khala.domain.memory.entities import Memory
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class MergeService:
    """Service for merging branches and resolving conflicts."""

    def __init__(self, db_client: SurrealDBClient, gemini_client: Optional[GeminiClient] = None):
        self.db_client = db_client
        self.gemini_client = gemini_client

    async def detect_conflicts(self, source_branch_id: str, target_branch_id: str) -> List[Dict[str, Any]]:
        """
        Detect conflicts between two branches.

        A conflict occurs if a memory was modified in both branches since the fork.
        """
        query = """
        SELECT
            source.id as source_id,
            target.id as target_id,
            source.updated_at as source_updated,
            target.updated_at as target_updated,
            source.content as source_content,
            target.content as target_content,
            source.fork_parent_id as parent_id
        FROM memory AS source, memory AS target
        WHERE source.branch_id = $sid
        AND target.branch_id = $tid
        AND source.fork_parent_id = target.fork_parent_id
        AND source.updated_at != target.updated_at;
        """

        params = {"sid": source_branch_id, "tid": target_branch_id}

        conflicts = []
        try:
            async with self.db_client.get_connection() as conn:
                result = await conn.query(query, params)
                if isinstance(result, list) and len(result) > 0:
                     if isinstance(result[0], dict) and 'result' in result[0]:
                         conflicts = result[0]['result']
                     else:
                         conflicts = result
        except Exception as e:
            logger.error(f"Failed to detect conflicts: {e}")

        return conflicts

    async def resolve_conflict_with_llm(self, conflict: Dict[str, Any]) -> str:
        """
        Resolve a text conflict using LLM (Strategy 158).
        """
        if not self.gemini_client:
            raise ValueError("Gemini client required for AI resolution")

        prompt = f"""
        Resolve the conflict between two versions of a memory.

        Version A (Source):
        {conflict['source_content']}

        Version B (Target):
        {conflict['target_content']}

        Merge them into a single coherent text that preserves key information from both.
        If they are contradictory, prefer Version A but note the discrepancy.

        Output only the merged text.
        """

        response = await self.gemini_client.generate_text(prompt, temperature=0.2)
        return response['content']

    async def merge_branches(self, source_branch_id: str, target_branch_id: str, resolution_strategy: str = "source_wins") -> Dict[str, Any]:
        """
        Merge source branch into target branch.
        """
        # 1. Detect conflicts
        conflicts = await self.detect_conflicts(source_branch_id, target_branch_id)

        resolved_count = 0

        # 2. Resolve conflicts
        for conflict in conflicts:
            resolved_content = ""
            if resolution_strategy == "source_wins":
                resolved_content = conflict['source_content']
            elif resolution_strategy == "target_wins":
                resolved_content = conflict['target_content']
            elif resolution_strategy == "llm" and self.gemini_client:
                resolved_content = await self.resolve_conflict_with_llm(conflict)
            else:
                # Default source wins
                resolved_content = conflict['source_content']

            # Update target memory
            target_id = conflict['target_id']

            query = "UPDATE type::thing('memory', $id) SET content = $content, updated_at = time::now(), metadata.merged_from = $src_id;"
            async with self.db_client.get_connection() as conn:
                await conn.query(query, {
                    "id": target_id,
                    "content": resolved_content,
                    "src_id": conflict['source_id']
                })
            resolved_count += 1

        return {"status": "success", "resolved_conflicts": resolved_count}
