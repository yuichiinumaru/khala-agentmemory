"""
Background processing infrastructure for KHALA.

Provides async job processing with Redis-based queuing,
priority scheduling, and comprehensive error handling.
"""

from .jobs.job_processor import JobProcessor, JobPriority, JobStatus, JobResult
from .jobs.consistency_job import ConsistencyJob

__all__ = [
    "JobProcessor",
    "JobPriority", 
    "JobStatus",
    "JobResult",
    "ConsistencyJob"
]
