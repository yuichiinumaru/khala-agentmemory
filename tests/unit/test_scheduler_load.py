"""Unit tests for scheduler load awareness (Task 106)."""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta

from khala.infrastructure.background.scheduler import BackgroundScheduler, RecurringTask, JobPriority
from khala.infrastructure.background.jobs.job_processor import JobProcessor
from khala.infrastructure.monitoring.health import HealthMonitor

@pytest.fixture
def mock_job_processor():
    return MagicMock(spec=JobProcessor)

@pytest.fixture
def mock_health_monitor():
    monitor = MagicMock(spec=HealthMonitor)
    # Default to healthy
    monitor.check_health = AsyncMock(return_value={"status": "healthy", "components": {}})
    return monitor

@pytest.mark.asyncio
async def test_scheduler_runs_task_when_healthy(mock_job_processor, mock_health_monitor):
    """Test that scheduler runs tasks when system is healthy."""
    scheduler = BackgroundScheduler(mock_job_processor, mock_health_monitor)

    # Add a task scheduled for now
    scheduler.add_task(
        name="test_task",
        job_type="test_job",
        interval_seconds=60,
        payload={"data": 1},
        priority=JobPriority.LOW
    )

    # Force next_run to be now or past
    scheduler.tasks["test_task"].next_run = datetime.now(timezone.utc) - timedelta(seconds=1)

    # Run _trigger_task directly to avoid loop complexity
    await scheduler._trigger_task(scheduler.tasks["test_task"])

    # Should have checked health
    mock_health_monitor.check_health.assert_called_once()

    # Should have submitted job
    mock_job_processor.submit_job.assert_called_once()

@pytest.mark.asyncio
async def test_scheduler_skips_low_priority_when_degraded(mock_job_processor, mock_health_monitor):
    """Test that scheduler skips LOW priority tasks when system is degraded."""
    # Set health to degraded
    mock_health_monitor.check_health.return_value = {
        "status": "degraded",
        "components": {"database": "slow"}
    }

    scheduler = BackgroundScheduler(mock_job_processor, mock_health_monitor)

    # Add LOW priority task
    scheduler.add_task(
        name="low_prio_task",
        job_type="test_job",
        interval_seconds=60,
        payload={},
        priority=JobPriority.LOW
    )

    scheduler.tasks["low_prio_task"].next_run = datetime.now(timezone.utc) - timedelta(seconds=1)

    await scheduler._trigger_task(scheduler.tasks["low_prio_task"])

    # Should have checked health
    mock_health_monitor.check_health.assert_called_once()

    # Should NOT have submitted job
    mock_job_processor.submit_job.assert_not_called()

@pytest.mark.asyncio
async def test_scheduler_runs_high_priority_even_when_degraded(mock_job_processor, mock_health_monitor):
    """Test that scheduler runs HIGH priority tasks even when system is degraded."""
    mock_health_monitor.check_health.return_value = {
        "status": "degraded",
        "components": {"database": "slow"}
    }

    scheduler = BackgroundScheduler(mock_job_processor, mock_health_monitor)

    # Add HIGH priority task
    scheduler.add_task(
        name="high_prio_task",
        job_type="test_job",
        interval_seconds=60,
        payload={},
        priority=JobPriority.HIGH
    )

    scheduler.tasks["high_prio_task"].next_run = datetime.now(timezone.utc) - timedelta(seconds=1)

    await scheduler._trigger_task(scheduler.tasks["high_prio_task"])

    # Should NOT have checked health (optimization: only check for LOW priority)
    # OR should check but proceed anyway.
    # In my implementation: "if self.health_monitor and task.priority == JobPriority.LOW:"
    # So it skips the health check block for HIGH priority.

    mock_health_monitor.check_health.assert_not_called()

    # Should have submitted job
    mock_job_processor.submit_job.assert_called_once()
