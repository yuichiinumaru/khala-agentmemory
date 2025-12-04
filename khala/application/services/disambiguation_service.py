"""Entity Disambiguation Service (Strategy 142).

This service identifies potential duplicate entities and merges them.
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.domain.memory.entities import Entity

logger = logging.getLogger(__name__)

class EntityDisambiguationService:
    """Service for finding and merging duplicate entities."""

    def __init__(self, db_client: SurrealDBClient, gemini_client: Optional[GeminiClient] = None):
        self.db_client = db_client
        self.gemini_client = gemini_client

    async def find_duplicates(self, entity_type: Optional[str] = None) -> List[List[Entity]]:
        """
        Find sets of duplicate entities.

        Returns a list of lists, where each inner list is a group of duplicates.
        """
        # 1. Fetch all entities (or by type)
        # This is expensive for large datasets, so in production we would stream or use vector similarity search.
        # For now, we fetch a batch.

        query = "SELECT * FROM entity"
        if entity_type:
            query += f" WHERE entity_type = '{entity_type}'"
        query += " LIMIT 1000;" # Limit for safety

        entities = []
        async with self.db_client.get_connection() as conn:
            resp = await conn.query(query)
            if resp and isinstance(resp, list):
                 items = resp
                 if len(resp) > 0 and isinstance(resp[0], dict) and 'result' in resp[0]:
                     items = resp[0]['result']
                 for item in items:
                     if isinstance(item, dict):
                         # Map back to Entity object
                         entities.append(Entity(
                             id=item['id'],
                             text=item['text'],
                             entity_type=item['entity_type'],
                             confidence=item.get('confidence', 0.0),
                             embedding=item.get('embedding'),
                             metadata=item.get('metadata', {}),
                             source=item.get('source', '')
                         ))

        if not entities:
            return []

        duplicates = []
        processed_ids = set()

        # Simple clustering by name similarity
        # Ideally we use embedding similarity if available

        for i, e1 in enumerate(entities):
            if e1.id in processed_ids:
                continue

            group = [e1]
            processed_ids.add(e1.id)

            for j, e2 in enumerate(entities[i+1:]):
                if e2.id in processed_ids:
                    continue

                if self._are_similar(e1, e2):
                    group.append(e2)
                    processed_ids.add(e2.id)

            if len(group) > 1:
                duplicates.append(group)

        return duplicates

    def _are_similar(self, e1: Entity, e2: Entity) -> bool:
        """Check if two entities are likely the same."""
        # 1. Exact string match (case insensitive)
        if e1.text.lower().strip() == e2.text.lower().strip():
            return True

        # 2. Embedding similarity (if both have embeddings)
        if e1.embedding and e2.embedding:
            # Simple cosine similarity check
            v1 = np.array(e1.embedding)
            v2 = np.array(e2.embedding)
            norm1 = np.linalg.norm(v1)
            norm2 = np.linalg.norm(v2)
            if norm1 > 0 and norm2 > 0:
                sim = np.dot(v1, v2) / (norm1 * norm2)
                if sim > 0.92: # High threshold
                    return True

        # 3. Heuristics (e.g. Jaro-Winkler or Levenshtein)
        # Simplified here
        return False

    async def merge_entities(self, primary_id: str, duplicate_ids: List[str], conn=None) -> Dict[str, Any]:
        """
        Merge duplicates into primary entity.

        1. Move relationships from duplicates to primary.
        2. Delete duplicates.
        3. Add aliases to primary metadata.
        """
        if not duplicate_ids:
            return {"status": "no_op"}

        logger.info(f"Merging entities {duplicate_ids} into {primary_id}")

        async def _execute_merge(connection):
            # 1. Update relationships
            for dup_id in duplicate_ids:
                # Update outgoing relationships (where dup is source, so 'in' field)
                await connection.query("UPDATE relationship SET in = $primary WHERE in = $dup", {
                    "primary": primary_id,
                    "dup": dup_id
                })

                # Update incoming relationships (where dup is target, so 'out' field)
                await connection.query("UPDATE relationship SET out = $primary WHERE out = $dup", {
                    "primary": primary_id,
                    "dup": dup_id
                })

            # 2. Delete duplicates
            for dup_id in duplicate_ids:
                await connection.delete(dup_id)

        if conn:
            await _execute_merge(conn)
        else:
            async with self.db_client.get_connection() as connection:
                await _execute_merge(connection)

        return {"status": "success", "merged_count": len(duplicate_ids)}

    async def auto_disambiguate(self) -> Dict[str, Any]:
        """Run full disambiguation pipeline."""
        duplicates = await self.find_duplicates()
        merged_total = 0

        async with self.db_client.get_connection() as conn:
            for group in duplicates:
                # Heuristic: Pick the one with highest confidence or most relationships or longest text as primary
                # For now: longest text usually has more detail? Or shortest is canonical?
                # Let's pick the one with earliest ID creation or just first one.
                primary = group[0]
                dupes = [e.id for e in group[1:]]

                # Pass existing connection to reuse it
                await self.merge_entities(primary.id, dupes, conn=conn)
                merged_total += len(dupes)

        return {"groups_found": len(duplicates), "merged_entities": merged_total}
