"""Service for self-healing index repair (Strategy 159).

This service is responsible for scanning the database for index inconsistencies,
such as missing embeddings, dimension mismatches, and other vector-related issues,
and automatically repairing them using available models.
"""

import logging
from typing import Dict, List, Any, Optional
import asyncio

from ...infrastructure.surrealdb.client import SurrealDBClient
from ...infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)


class IndexRepairService:
    """Service for detecting and repairing index inconsistencies."""

    def __init__(self, db_client: SurrealDBClient, gemini_client: GeminiClient):
        """Initialize the service.

        Args:
            db_client: Client for SurrealDB operations
            gemini_client: Client for generating embeddings
        """
        self.db_client = db_client
        self.gemini_client = gemini_client
        self.vector_dimension = 768  # Standard dimension for current model

    async def scan_and_repair(
        self,
        fix: bool = True,
        batch_size: int = 50,
        scan_all: bool = False
    ) -> Dict[str, Any]:
        """Scan for index issues and optionally repair them.

        Args:
            fix: Whether to apply fixes or just report
            batch_size: Number of records to process in one go
            scan_all: If True, continues processing batches until no issues are found (with limit)

        Returns:
            Report of issues found and repaired
        """
        report = {
            "scanned_count": 0,
            "issues_found": {
                "missing_embeddings": 0,
                "dimension_mismatch": 0,
                "other_errors": 0
            },
            "repaired_count": 0,
            "errors": []
        }

        max_iterations = 20 if scan_all else 1
        iteration = 0

        while iteration < max_iterations:
            iteration += 1
            issues_found_this_batch = False

            try:
                # 1. Check for missing embeddings
                missing_query = """
                SELECT id, content FROM memory
                WHERE embedding IS NONE
                AND content != ''
                AND content != NONE
                LIMIT $limit;
                """

                async with self.db_client.get_connection() as conn:
                    response = await conn.query(missing_query, {"limit": batch_size})
                    if isinstance(response, list) and len(response) > 0:
                         if 'result' in response[0]:
                             missing_records = response[0]['result']
                         else:
                             missing_records = response
                    else:
                        missing_records = []

                if not isinstance(missing_records, list):
                    missing_records = []

                if missing_records:
                    issues_found_this_batch = True
                    report["issues_found"]["missing_embeddings"] += len(missing_records)
                    report["scanned_count"] += len(missing_records)

                    if fix:
                        await self._repair_missing_embeddings(missing_records, report)

                # 2. Check for dimension mismatch (only if we have capacity in this batch or just checked missing)
            # This is harder to query efficiently in SurrealDB without a computed field for length.
            # However, we can use a function or check specific problematic ones if known.
            # Strategy 159 implies "Self-Healing", so we should try to catch these.
            # We can use `array::len(embedding) != 768` in WHERE clause if supported.

                mismatch_query = """
                SELECT id, content FROM memory
                WHERE embedding IS NOT NONE
                AND array::len(embedding) != $dim
                LIMIT $limit;
                """

                remaining_limit = batch_size - len(missing_records)
                if remaining_limit > 0:
                    async with self.db_client.get_connection() as conn:
                        response = await conn.query(mismatch_query, {"dim": self.vector_dimension, "limit": remaining_limit})
                        if isinstance(response, list) and len(response) > 0:
                             if 'result' in response[0]:
                                 mismatch_records = response[0]['result']
                             else:
                                 mismatch_records = response
                        else:
                            mismatch_records = []

                    if not isinstance(mismatch_records, list):
                        mismatch_records = []

                    if mismatch_records:
                        issues_found_this_batch = True
                        report["issues_found"]["dimension_mismatch"] += len(mismatch_records)
                        report["scanned_count"] += len(mismatch_records)

                        if fix:
                            await self._repair_missing_embeddings(mismatch_records, report) # Reuse logic as it's just re-embedding

            except Exception as e:
                logger.error(f"Error during index repair scan: {e}")
                report["errors"].append(str(e))
                break # Stop iterating on error

            # If no issues found in this batch and scan_all is True, we can likely stop early
            # unless we think there are more pages.
            # However, if we found 0 issues, future pages are likely empty too unless the query order is random.
            # Assuming SurrealDB returns stable order or we fixed the ones found, 0 issues means we are clean.
            if not issues_found_this_batch and scan_all:
                break

        return report

    async def _repair_missing_embeddings(self, records: List[Dict[str, Any]], report: Dict[str, Any]) -> None:
        """Repair a batch of records by generating embeddings."""
        try:
            # Filter valid records first to ensure alignment
            valid_records = [r for r in records if r.get('content')]
            if not valid_records:
                return

            texts = [r['content'] for r in valid_records]

            # Generate embeddings in batch
            embeddings = await self.gemini_client.generate_embeddings(texts)

            if len(embeddings) != len(texts):
                logger.error(f"Mismatch in generated embeddings count: got {len(embeddings)}, expected {len(texts)}")
                report["errors"].append("Embedding generation count mismatch")
                return

            # Update records - iterate over valid_records which matches embeddings list
            update_count = 0
            for i, record in enumerate(valid_records):
                try:
                    memory_id = record['id']
                    # Ensure ID format (handle 'memory:id' vs 'id')
                    # SurrealDB client usually handles this, but raw query results return full ID

                    # Update the memory
                    await self.db_client.update_memory_field(
                        memory_id=memory_id,
                        field="embedding",
                        value=embeddings[i]
                    )

                    # Also update metadata to track repair
                    await self.db_client.update_memory_field(
                        memory_id=memory_id,
                        field="metadata.last_repaired_at",
                        value=str(asyncio.get_event_loop().time()) # or datetime
                    )

                    update_count += 1

                except Exception as e:
                    logger.error(f"Failed to update memory {record.get('id')}: {e}")
                    report["errors"].append(f"Update failed for {record.get('id')}: {str(e)}")

            report["repaired_count"] += update_count

        except Exception as e:
            logger.error(f"Error repairing embeddings batch: {e}")
            report["errors"].append(str(e))
