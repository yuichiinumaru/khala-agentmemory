"""
Deduplication Service (Strategy 12).

Implements a two-pass system to eliminate exact and semantic duplicates.
1. Exact Match: Hash-based (content_hash)
2. Semantic Match: Vector-based (cosine similarity)
"""

import hashlib
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass

from khala.domain.memory.entities import Memory
from khala.domain.memory.value_objects import EmbeddingVector
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

@dataclass
class DuplicateResult:
    is_duplicate: bool
    duplicate_of_id: Optional[str] = None
    similarity_score: float = 0.0
    duplicate_type: str = "none"  # "exact", "semantic", "none"

class DeduplicationService:
    """Service for detecting and handling duplicate memories."""

    def __init__(self, db_client: SurrealDBClient, semantic_threshold: float = 0.98):
        self.db_client = db_client
        self.semantic_threshold = semantic_threshold

    def compute_hash(self, content: str, user_id: str) -> str:
        """Compute SHA256 hash of content + user_id."""
        return hashlib.sha256(f"{content}{user_id}".encode()).hexdigest()

    async def check_exact_duplicate(self, content_hash: str) -> Optional[str]:
        """Check for exact duplicate using content hash."""
        query = "SELECT id FROM memory WHERE content_hash = $hash LIMIT 1;"
        params = {"hash": content_hash}

        async with self.db_client.get_connection() as conn:
            response = await conn.query(query, params)

            if response and isinstance(response, list) and len(response) > 0:
                item = response[0]
                if isinstance(item, dict):
                    # Handle wrapper
                    if 'status' in item and 'result' in item:
                        if item['status'] == 'OK' and item['result']:
                            record = item['result'][0]
                            return self._clean_id(record['id'])
                    # Handle direct record
                    elif 'id' in item:
                        return self._clean_id(item['id'])

            return None

    async def check_semantic_duplicate(
        self,
        embedding: EmbeddingVector,
        user_id: str
    ) -> Tuple[Optional[str], float]:
        """Check for semantic duplicate using vector similarity."""
        if not embedding or not embedding.values:
            return None, 0.0

        # Use search_memories_by_vector with very high threshold
        results = await self.db_client.search_memories_by_vector(
            embedding=embedding,
            user_id=user_id,
            top_k=1,
            min_similarity=self.semantic_threshold
        )

        if results:
            match = results[0]
            similarity = match.get('similarity', 0.0)

            # Double check threshold (client might have different default)
            if similarity >= self.semantic_threshold:
                return self._clean_id(match['id']), similarity

        return None, 0.0

    async def check_duplicate(self, memory: Memory) -> DuplicateResult:
        """
        Check if a memory is a duplicate (Exact or Semantic).
        Returns DuplicateResult.
        """
        # 1. Exact Match
        content_hash = self.compute_hash(memory.content, memory.user_id)
        exact_match_id = await self.check_exact_duplicate(content_hash)

        if exact_match_id and exact_match_id != memory.id:
            logger.info(f"Exact duplicate detected: {memory.id} -> {exact_match_id}")
            return DuplicateResult(
                is_duplicate=True,
                duplicate_of_id=exact_match_id,
                similarity_score=1.0,
                duplicate_type="exact"
            )

        # 2. Semantic Match
        if memory.embedding:
            semantic_match_id, score = await self.check_semantic_duplicate(
                memory.embedding,
                memory.user_id
            )

            if semantic_match_id and semantic_match_id != memory.id:
                logger.info(f"Semantic duplicate detected: {memory.id} -> {semantic_match_id} (score: {score})")
                return DuplicateResult(
                    is_duplicate=True,
                    duplicate_of_id=semantic_match_id,
                    similarity_score=score,
                    duplicate_type="semantic"
                )

        return DuplicateResult(is_duplicate=False)

    def _clean_id(self, record_id: str) -> str:
        """Strip table prefix from ID if present."""
        if ":" in str(record_id):
            return str(record_id).split(":", 1)[1]
        return str(record_id)
