"""Background scheduler for KHALA.

Handles scheduling of recurring maintenance tasks like decay scoring,
consistency checks, and consolidation.
"""

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Optional, Any, Callable, Coroutine
from dataclasses import dataclass

from .jobs.job_processor import JobProcessor, JobPriority

logger = logging.getLogger(__name__)

@dataclass
class RecurringTask:
    """Definition of a recurring task."""
    name: str
    job_type: str
    interval_seconds: int
    payload: Dict[str, Any]
    priority: JobPriority = JobPriority.LOW
    last_run: Optional[datetime] = None
    next_run: Optional[datetime] = None

class BackgroundScheduler:
    """Simple scheduler for recurring background jobs."""

    def __init__(self, job_processor: JobProcessor):
        """Initialize scheduler.

        Args:
            job_processor: JobProcessor instance to submit jobs to.
        """
        self.job_processor = job_processor
        self.tasks: Dict[str, RecurringTask] = {}
        self.is_running = False
        self._scheduler_task: Optional[asyncio.Task] = None

    def add_task(
        self,
        name: str,
        job_type: str,
        interval_seconds: int,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.LOW
    ) -> None:
        """Register a recurring task."""
        task = RecurringTask(
            name=name,
            job_type=job_type,
            interval_seconds=interval_seconds,
            payload=payload,
            priority=priority,
            next_run=datetime.now(timezone.utc) # Run immediately on start? Or wait?
            # Let's say we schedule it for now, so it runs shortly after start.
        )
        self.tasks[name] = task
        logger.info(f"Registered recurring task: {name} (every {interval_seconds}s)")

    async def start(self) -> None:
        """Start the scheduler loop."""
        if self.is_running:
            return

        self.is_running = True
        self._scheduler_task = asyncio.create_task(self._loop())
        logger.info("Background scheduler started")

    async def stop(self) -> None:
        """Stop the scheduler."""
        if not self.is_running:
            return

        self.is_running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
            try:
                await self._scheduler_task
            except asyncio.CancelledError:
                pass
        logger.info("Background scheduler stopped")

    async def _loop(self) -> None:
        """Main scheduler loop."""
        while self.is_running:
            try:
                now = datetime.now(timezone.utc)

                for task in self.tasks.values():
                    if not task.next_run or task.next_run <= now:
                        # Time to run
                        await self._trigger_task(task)

                        # Schedule next run
                        task.last_run = now
                        task.next_run = now + timedelta(seconds=task.interval_seconds)

                # Check every minute
                await asyncio.sleep(60)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Scheduler loop error: {e}")
                await asyncio.sleep(60)

    async def _trigger_task(self, task: RecurringTask) -> None:
        """Submit the task to the job processor."""
        try:
            # We might need to fetch dynamic payload data here (e.g. all memory IDs)
            # For now, assume payload contains what's needed or is a command to process "all"

            # Special handling for "decay_scoring" if we need to fetch IDs
            # But ideally the job itself handles "all" if ids are missing, or we have a specialized job for "scan_all".
            # The current DecayScoringJob expects "memory_ids".
            # We should update DecayScoringJob to handle "all" or fetch IDs if list is empty?
            # Or we fetch IDs here. Fetching here is safer for the job logic simplicity.

            payload = task.payload.copy()

            if task.job_type == "decay_scoring" and not payload.get("memory_ids"):
                 # If no specific IDs, assume we want to process a batch of old memories
                 # This requires DB access.
                 # Let's assume for now we submit it and the job handles it or we pass a flag
                 # But the job code I saw expects memory_ids and raises ValueError if missing.
                 # I should probably update the JobProcessor to handle "process all" or query for candidates.

                 # Since I can't easily inject DB here without making Scheduler complex,
                 # I will update the JobProcessor's _execute_decay_scoring to fetch candidates if list is empty.
                 pass

            await self.job_processor.submit_job(
                job_type=task.job_type,
                payload=payload,
                priority=task.priority
            )
            logger.info(f"Triggered task: {task.name}")

        except Exception as e:
            logger.error(f"Failed to trigger task {task.name}: {e}")

# Factory
def create_scheduler(job_processor: JobProcessor) -> BackgroundScheduler:
    """Create and configure the scheduler with default tasks."""
    scheduler = BackgroundScheduler(job_processor)

    # Add default maintenance tasks

    # 1. Daily Decay Scoring
    scheduler.add_task(
        name="daily_decay_scoring",
        job_type="decay_scoring",
        interval_seconds=86400, # 24 hours
        payload={"scan_all": True}, # We'll need to update job processor to handle this
        priority=JobPriority.LOW
    )

    # 2. Weekly Consistency Check (Example)
    # scheduler.add_task(...)

    return scheduler
