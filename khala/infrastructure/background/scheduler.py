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
from ..monitoring.health import HealthMonitor

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

    def __init__(self, job_processor: JobProcessor, health_monitor: Optional[HealthMonitor] = None):
        """Initialize scheduler.

        Args:
            job_processor: JobProcessor instance to submit jobs to.
            health_monitor: Optional HealthMonitor to check system load before scheduling.
        """
        self.job_processor = job_processor
        self.health_monitor = health_monitor
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
            # 106. Consolidation Schedule: Check system load before triggering low priority tasks
            if self.health_monitor and task.priority == JobPriority.LOW:
                health_status = await self.health_monitor.check_health()
                if health_status.get("status") == "degraded":
                    logger.warning(
                        f"Skipping task {task.name} due to system load (degraded health). "
                        f"Details: {health_status.get('components')}"
                    )
                    # Reschedule for check in 5 minutes instead of full interval?
                    # For simplicity, we just skip this run and wait for the loop to pick it up again?
                    # No, the loop advances next_run only after calling _trigger_task.
                    # If we return here without doing anything, the loop (in _loop)
                    # will advance next_run anyway because it calls this, then updates times.
                    # That is acceptable for "skipping".
                    # If we want to "postpone" by a short amount, we should probably throw an exception
                    # or handle it in the caller.
                    # But skipping a maintenance job once is usually fine.
                    return

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
def create_scheduler(job_processor: JobProcessor, health_monitor: Optional[HealthMonitor] = None) -> BackgroundScheduler:
    """Create and configure the scheduler with default tasks."""
    scheduler = BackgroundScheduler(job_processor, health_monitor)

    # Add default maintenance tasks

    # 1. Daily Decay Scoring
    scheduler.add_task(
        name="daily_decay_scoring",
        job_type="decay_scoring",
        interval_seconds=86400, # 24 hours
        payload={"scan_all": True}, # We'll need to update job processor to handle this
        priority=JobPriority.LOW
    )

    # 2. Weekly Consolidation
    scheduler.add_task(
        name="weekly_consolidation",
        job_type="consolidation",
        interval_seconds=604800, # 7 days
        payload={"scan_all": True},
        priority=JobPriority.LOW
    )

    # 3. Weekly Deduplication
    scheduler.add_task(
        name="weekly_deduplication",
        job_type="deduplication",
        interval_seconds=604800, # 7 days
        payload={"scan_all": True},
        priority=JobPriority.LOW
    )

    return scheduler
