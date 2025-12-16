import asyncio
import logging
from datetime import datetime, timezone
from khala.infrastructure.persistence.job_repository import JobRepository
from khala.application.services.memory_lifecycle import MemoryLifecycleService
from khala.domain.jobs.entities import JobStatus

logger = logging.getLogger(__name__)

class ConsolidationWorker:
    def __init__(self, job_repo: JobRepository, lifecycle_service: MemoryLifecycleService):
        self.job_repo = job_repo
        self.lifecycle_service = lifecycle_service
        self.running = False

    async def start(self, poll_interval: int = 60):
        self.running = True
        logger.info("Consolidation Worker started.")
        while self.running:
            try:
                jobs = await self.job_repo.get_pending(limit=1)
                for job in jobs:
                    if job.type == "consolidation":
                        await self._process_job(job)
            except Exception as e:
                logger.error(f"Worker loop error: {e}")

            await asyncio.sleep(poll_interval)

    async def stop(self):
        self.running = False

    async def _process_job(self, job):
        logger.info(f"Processing consolidation job {job.id}")
        job.status = JobStatus.RUNNING
        job.started_at = datetime.now(timezone.utc)
        await self.job_repo.update(job)

        try:
            user_id = job.payload.get("user_id")
            if not user_id:
                raise ValueError("Missing user_id in job payload")

            result = await self.lifecycle_service.consolidate_memories(user_id, force=True)

            job.status = JobStatus.COMPLETED
            job.result = {"consolidated_count": result}
        except Exception as e:
            logger.error(f"Job {job.id} failed: {e}")
            job.status = JobStatus.FAILED
            job.error = str(e)

        job.completed_at = datetime.now(timezone.utc)
        await self.job_repo.update(job)
