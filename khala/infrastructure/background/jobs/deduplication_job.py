"""Deduplication job for KHALA.

This job identifies and removes duplicate memories to maintain system hygiene.
"""

import logging
from typing import Dict, Any

from ....infrastructure.surrealdb.client import SurrealDBClient
from ....infrastructure.persistence.surrealdb_repository import SurrealDBMemoryRepository
from ....application.services.memory_lifecycle import MemoryLifecycleService

logger = logging.getLogger(__name__)

class DeduplicationJob:
    """Job to deduplicate memories."""
    
    def __init__(self, db_client: SurrealDBClient):
        self.db_client = db_client
        self.repository = SurrealDBMemoryRepository(db_client)
        self.lifecycle_service = MemoryLifecycleService(repository=self.repository)
        
    async def execute(self, job_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute deduplication.
        
        Args:
            job_payload: Dict containing 'user_id' or 'scan_all'
            
        Returns:
            Dict with results
        """
        user_id = job_payload.get("user_id")
        scan_all = job_payload.get("scan_all", False)
        
        users_to_process = [user_id] if user_id else []
        
        if not users_to_process and scan_all:
             # Fetch all distinct user_ids
             query = "SELECT user_id FROM memory GROUP BY user_id;"
             async with self.db_client.get_connection() as conn:
                response = await conn.query(query)
                if response and isinstance(response, list):
                    # Handle SurrealDB response wrapper
                    items = response
                    if len(response) > 0 and isinstance(response[0], dict) and 'result' in response[0]:
                        items = response[0]['result']
                    
                    users_to_process = [
                        item['user_id'] for item in items 
                        if isinstance(item, dict) and 'user_id' in item and item['user_id']
                    ]

        total_removed = 0
        users_processed = 0
        
        for uid in users_to_process:
            try:
                count = await self.lifecycle_service.deduplicate_memories(uid)
                total_removed += count
                users_processed += 1
            except Exception as e:
                logger.error(f"Deduplication failed for user {uid}: {e}")
                
        return {
            "status": "completed",
            "users_processed": users_processed,
            "duplicates_removed": total_removed
        }
