"""
Background processing infrastructure for KHALA.

Provides async job processing with Redis-based queuing,
priority scheduling, and comprehensive error handling.
"""

from .jobs.job_processor import JobProcessor, JobPriority, JobStatus
from .jobs.job_types.base_job import BaseJob, JobResult
from .jobs.job_types.decay_scoring import DecayScoringJob
from .jobs.job_types.consolidation import ConsolidationJob
from .jobs.job_types.deduplication import DeduplicationJob

__all__ = [
    "JobProcessor",
    "JobPriority", 
    "JobStatus",
    "BaseJob",
    "JobResult",
    "DecayScoringJob",
    "ConsolidationJob", 
    "DeduplicationJob"
]
