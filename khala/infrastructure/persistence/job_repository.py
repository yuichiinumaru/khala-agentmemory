from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
import logging

from khala.domain.jobs.entities import Job, JobStatus
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class JobRepository:
    def __init__(self, client: SurrealDBClient):
        self.client = client
        self.table = "jobs"

    async def create(self, job: Job) -> str:
        """Create a new job."""
        data = {
            "id": job.id,
            "type": job.type,
            "payload": job.payload,
            "status": job.status.value,
            "created_at": job.created_at.isoformat(),
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "result": job.result,
            "error": job.error
        }

        # Remove None values if necessary, or DB handles it
        try:
            # Assumes client.create handles table prefix or we format it
            # Assuming client.create(table, data)
            # Or client.query("CREATE jobs CONTENT $data")
            # Using query for safety
            query = f"CREATE {self.table} CONTENT $data"
            async with self.client.get_connection() as conn:
                resp = await conn.query(query, {"data": data})
                # Extract ID
                if isinstance(resp, list) and resp:
                    if isinstance(resp[0], dict):
                        return resp[0].get('id', job.id)
                return job.id
        except Exception as e:
            logger.error(f"Failed to create job: {e}")
            raise

    async def get_pending(self, limit: int = 10) -> List[Job]:
        """Get pending jobs."""
        query = f"SELECT * FROM {self.table} WHERE status = 'pending' ORDER BY created_at ASC LIMIT $limit"
        try:
            async with self.client.get_connection() as conn:
                resp = await conn.query(query, {"limit": limit})
                # Parse
                return self._parse_jobs(resp)
        except Exception as e:
            logger.error(f"Failed to fetch pending jobs: {e}")
            return []

    async def update(self, job: Job) -> None:
        """Update job status."""
        query = f"UPDATE {job.id} CONTENT $data"
        data = {
            "status": job.status.value,
            "started_at": job.started_at.isoformat() if job.started_at else None,
            "completed_at": job.completed_at.isoformat() if job.completed_at else None,
            "result": job.result,
            "error": job.error
        }
        try:
            async with self.client.get_connection() as conn:
                await conn.query(query, {"data": data})
        except Exception as e:
            logger.error(f"Failed to update job {job.id}: {e}")
            raise

    def _parse_jobs(self, response: Any) -> List[Job]:
        jobs = []
        if isinstance(response, list) and response:
            items = response
            if isinstance(response[0], dict) and 'result' in response[0]:
                items = response[0]['result']

            for item in items:
                if not isinstance(item, dict): continue
                try:
                    jobs.append(Job(
                        id=item.get("id"),
                        type=item.get("type"),
                        payload=item.get("payload", {}),
                        status=JobStatus(item.get("status", "pending")),
                        created_at=datetime.fromisoformat(item.get("created_at")),
                        started_at=datetime.fromisoformat(item.get("started_at")) if item.get("started_at") else None,
                        completed_at=datetime.fromisoformat(item.get("completed_at")) if item.get("completed_at") else None,
                        result=item.get("result"),
                        error=item.get("error")
                    ))
                except Exception as e:
                    logger.warning(f"Failed to parse job item: {e}")
        return jobs
