import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timezone

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.embeddings.openai_embedding import OpenAIEmbedding

logger = logging.getLogger(__name__)

class SelfHealingIndexJob:
    """Background job to re-index low-performing or missing vectors.

    Strategy 159: Self-Healing Index.
    """

    def __init__(self, db_client: SurrealDBClient, embedding_service: Optional[OpenAIEmbedding] = None):
        self.db_client = db_client
        self.embedding_service = embedding_service or OpenAIEmbedding()

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the self-healing index job.

        Args:
            payload: Job parameters including:
                - limit: Max records to process (default 100)
                - ids: Optional list of IDs to target
                - table: Table to heal (default "memory")

        Returns:
            Job statistics
        """
        limit = payload.get("limit", 100)
        # Support both 'ids' and 'memory_ids' for flexibility
        target_ids = payload.get("ids", payload.get("memory_ids", []))
        table = payload.get("table", "memory")

        # Determine text field based on table
        text_field = "text" if table == "entity" else "content"

        processed_count = 0
        failed_count = 0
        candidates = []

        try:
            # 1. Identify candidates (missing embeddings)
            if target_ids:
                query = f"SELECT id, {text_field} FROM type::table($table) WHERE id IN $ids;"
                params = {"ids": target_ids, "table": table}

                async with self.db_client.get_connection() as conn:
                    response = await conn.query(query, params)
                    if response and isinstance(response, list) and len(response) > 0:
                        if isinstance(response[0], dict) and 'result' in response[0]:
                             candidates = response[0]['result']
                        else:
                             candidates = response
            else:
                # Find records with missing embeddings
                query = f"SELECT id, {text_field} FROM type::table($table) WHERE embedding IS NONE LIMIT $limit;"
                params = {"limit": limit, "table": table}

                async with self.db_client.get_connection() as conn:
                    response = await conn.query(query, params)
                    if response and isinstance(response, list) and len(response) > 0:
                         if isinstance(response[0], dict) and 'result' in response[0]:
                             candidates = response[0]['result']
                         else:
                             candidates = response

            logger.info(f"Found {len(candidates)} candidates for re-indexing in {table}")

            # 2. Process candidates
            for item in candidates:
                try:
                    # Parse ID
                    raw_id = str(item['id'])
                    record_id = raw_id
                    if ":" in raw_id:
                        record_id = raw_id.split(":")[1]

                    content = item.get(text_field)

                    if not content:
                        logger.warning(f"Record {record_id} in {table} has no content, skipping.")
                        continue

                    # Generate embedding
                    embedding = await self.embedding_service.get_embedding(content)

                    if not embedding:
                        logger.warning(f"Failed to generate embedding for {record_id}")
                        failed_count += 1
                        continue

                    # Update record
                    update_query = """
                    UPDATE type::thing($table, $id)
                    SET embedding = $embedding;
                    """

                    # Add updated_at only if it is memory table which has it defined
                    if table == "memory":
                        update_query = """
                        UPDATE type::thing($table, $id)
                        SET embedding = $embedding,
                            updated_at = time::now();
                        """

                    update_params = {
                        "table": table,
                        "id": record_id,
                        "embedding": embedding
                    }

                    async with self.db_client.get_connection() as conn:
                        await conn.query(update_query, update_params)

                    processed_count += 1

                except Exception as e:
                    logger.error(f"Failed to re-index record {item.get('id')}: {e}")
                    failed_count += 1

            return {
                "processed": processed_count,
                "failed": failed_count,
                "candidates_found": len(candidates),
                "table": table
            }

        except Exception as e:
            logger.error(f"Self-healing index job failed: {e}")
            raise
