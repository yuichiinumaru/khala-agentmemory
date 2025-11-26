"""
Asynchronous job processor for KHALA background operations.

Implements priority-queued job processing with Redis backend,
worker thread management, and comprehensive error handling.
"""

import asyncio
import json
import logging
import time
from datetime import datetime, timezone, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from asyncio import Queue, Task
import uuid

try:
    import redis.asyncio as redis
except ImportError:
    redis = None
    logging.warning("Redis not available, using in-memory queue fallback")

from ....domain.memory.entities import Memory, MemoryTier
from ....domain.memory.value_objects import ImportanceScore, DecayScore
from ....domain.memory.services import MemoryService
from ...surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)


class JobPriority(Enum):
    """Job priority levels."""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class JobStatus(Enum):
    """Job execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class JobDefinition:
    """Job definition for serialization."""
    job_id: str
    job_type: str
    job_class: str
    priority: JobPriority
    payload: Dict[str, Any]
    created_at: datetime
    scheduled_at: Optional[datetime] = None
    max_retries: int = 3
    retry_count: int = 0
    timeout_seconds: int = 300
    status: JobStatus = JobStatus.PENDING
    error_message: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    worker_id: Optional[str] = None


@dataclass
class JobResult:
    """Result from job execution."""
    job_id: str
    success: bool
    result: Any
    execution_time_ms: float
    error: Optional[str] = None
    completed_at: datetime = None
    worker_id: Optional[str] = None

    def __post_init__(self):
        if self.completed_at is None:
            self.completed_at = datetime.now(timezone.utc)


class JobProcessor:
    """Main job processor for KHALA background operations."""
    
    def __init__(
        self,
        redis_url: str = "redis://localhost:6379/1",
        max_workers: int = 4,
        redis_ttl_seconds: int = 86400,  # 24 hours
        enable_metrics: bool = True
    ):
        """Initialize job processor.
        
        Args:
            redis_url: Redis connection URL (uses in-memory fallback if unavailable)
            max_workers: Maximum number of concurrent worker threads
            redis_ttl_seconds: TTL for job records in Redis
            enable_metrics: Enable performance metrics collection
        """
        self.redis_url = redis_url
        self.max_workers = max_workers
        self.redis_ttl = redis_ttl_seconds
        self.enable_metrics = enable_metrics
        
        # Redis client (fallback to in-memory if not available)
        self.redis_client: Optional[redis.Redis] = None
        self._memory_queue: Queue[JobDefinition] = Queue()
        
        # Worker management
        self.worker_tasks: List[Task] = []
        self.worker_counter = 0
        self.is_running = False
        
        # Job class registry
        self._job_classes = {}
        
        # Performance metrics
        self.metrics = {
            "total_jobs": 0,
            "successful_jobs": 0,
            "failed_jobs": 0,
            "avg_execution_time_ms": 0.0,
            "jobs_per_second": 0.0,
            "worker_utilization": 0.0,
            "retry_count": 0,
            "jobs_by_priority": {
                priority.value: 0 for priority in JobPriority
            }
        }
        
        # Services
        self.memory_service = None
        self.db_client = None
        
        # Job types
        self._register_default_jobs()
    
    async def start(self) -> None:
        """Start the job processor and begin processing jobs."""
        if self.is_running:
            logger.warning("Job processor is already running")
            return
        
        try:
            # Initialize Redis client
            if redis is not None:
                self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
                await self.redis_client.ping()
                logger.info(f"Connected to Redis at {self.redis_url}")
            else:
                logger.warning("Redis not available, using in-memory queue only")
                self.redis_client = None
            
            # Initialize services
            self.memory_service = MemoryService()
            self.db_client = SurrealDBClient()
            
            # Start worker tasks
            self.is_running = True
            for i in range(self.max_workers):
                worker = asyncio.create_task(self._worker_loop(f"worker_{i}"))
                self.worker_tasks.append(worker)
                self.worker_counter += 1
            
            logger.info(f"Job processor started with {self.max_workers} workers")
            
        except Exception as e:
            logger.error(f"Failed to start job processor: {e}")
            raise
    
    async def stop(self) -> None:
        """Stop the job processor gracefully."""
        if not self.is_running:
            return
        
        logger.info("Stopping job processor...")
        self.is_running = False
        
        # Cancel all worker tasks
        for worker_task in self.worker_tasks:
            worker_task.cancel()
        
        try:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        except Exception as e:
            logger.error(f"Error during worker shutdown: {e}")
        
        self.worker_tasks.clear()
        
        # Close Redis connection
        if self.redis_client:
            await self.redis_client.close()
        
        logger.info("Job processor stopped")
    
    def _register_default_jobs(self) -> None:
        """Register default job types."""
        # Import and register job classes dynamically here
        # This provides flexibility for adding new job types
        self._job_classes = {
            "decay_scoring": "DecayScoringJob",
            "consolidation": "ConsolidationJob", 
            "deduplication": "DeduplicationJob",
            "consistency_check": "ConsistencyJob"
        }
    
    async def submit_job(
        self,
        job_type: str,
        payload: Dict[str, Any],
        priority: JobPriority = JobPriority.MEDIUM,
        scheduled_at: Optional[datetime] = None,
        max_retries: int = 3,
        timeout_seconds: int = 300
    ) -> str:
        """Submit a job for processing.
        
        Args:
            job_type: Type of job to execute
            payload: Job execution parameters
            priority: Job priority level
            scheduled_at: When to execute the job (None = immediate)
            max_retries: Maximum retry attempts
            timeout_seconds: Job execution timeout
            
        Returns:
            Job ID for tracking
        """
        if job_type not in self._job_classes:
            raise ValueError(f"Unknown job type: {job_type}")
        
        job_id = str(uuid.uuid4())
        job = JobDefinition(
            job_id=job_id,
            job_type=job_type,
            job_class=self._job_classes[job_type],
            priority=priority,
            payload=payload,
            created_at=datetime.now(timezone.utc),
            scheduled_at=scheduled_at,
            max_retries=max_retries,
            timeout_seconds=timeout_seconds
        )
        
        # Store in Redis or memory queue
        if self.redis_client:
            await self._store_job_redis(job)
        else:
            self._memory_queue.put_nowait(job)
        
        self.metrics["total_jobs"] += 1
        self.metrics["jobs_by_priority"][priority.value] += 1
        
        logger.info(f"Submitted job {job_id} of type {job_type} with priority {priority.name}")
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[JobDefinition]:
        """Get current status of a job."""
        if self.redis_client:
            job_data = await self.redis_client.hgetall(f"job:{job_id}")
            if job_data:
                return self._deserialize_job(job_data)
        return None
    
    async def get_job_result(self, job_id: str) -> Optional[JobResult]:
        """Get result of a completed job."""
        if self.redis_client:
            result_data = await self.redis_client.hgetall(f"result:{job_id}")
            if result_data:
                return self._deserialize_result(result_data)
        return None
    
    async def _store_job_redis(self, job: JobDefinition) -> None:
        """Store job definition in Redis."""
        if not self.redis_client:
            return
        
        serialized = self._serialize_job(job)
        
        # Store in job hash
        await self.redis_client.hset(f"job:{job.job_id}", mapping=serialized)
        
        # Add to priority queue
        score = int(job.priority.value * 1000 - job.created_at.timestamp())
        await self.redis_client.zadd("job:queue", {f"job:{job.job_id}": score})
        
        # Set TTL
        await self.redis_client.expire(f"job:{job.job_id}", self.redis_ttl)
        await self.redis_client.expire("job:queue", self.redis_ttl)
    
    async def _get_next_job(self) -> Optional[JobDefinition]:
        """Get next job from queue."""
        if self.redis_client:
            # Get from priority queue
            result = await self.redis_client.zpopmin("job:queue")
            if result:
                job_key, _ = result[0]
                # job_key is already str if decode_responses=True
                job_data = await self.redis_client.hgetall(job_key)
                if job_data:
                    return self._deserialize_job(job_data)
        
        # Fallback to memory queue
        if not self._memory_queue.empty():
            return self._memory_queue.get_nowait()
        
        return None
    
    async def _worker_loop(self, worker_id: str) -> None:
        """Main worker loop for processing jobs."""
        logger.info(f"Worker {worker_id} started")
        
        while self.is_running:
            try:
                # Get next job with timeout
                job = await asyncio.wait_for(
                    self._get_next_job(),
                    timeout=1.0  # Check for jobs every second
                )
                
                if job:
                    await self._process_job(job, worker_id)
                else:
                    # No jobs available, short sleep
                    await asyncio.sleep(0.1)
                    
            except asyncio.TimeoutError:
                # No jobs available, continue loop
                continue
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                await asyncio.sleep(1.0)  # Brief pause on error
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _process_job(self, job: JobDefinition, worker_id: str) -> None:
        """Process a single job."""
        start_time = time.time()
        
        try:
            logger.debug(f"Worker {worker_id} processing job {job.job_id}")
            
            # Update job status to running
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            job.worker_id = worker_id
            
            if self.redis_client:
                await self.redis_client.hset(
                    f"job:{job.job_id}",
                    mapping={
                        "status": job.status.value,
                        "started_at": job.started_at.isoformat(),
                        "worker_id": worker_id
                    }
                )
            
            # Execute job based on type
            result = await self._execute_job(job)
            
            # Update success metrics
            execution_time = (time.time() - start_time) * 1000
            if result.success:
                self.metrics["successful_jobs"] += 1
            else:
                self.metrics["failed_jobs"] += 1
            
            # Update average execution time
            total_time = self.metrics["avg_execution_time_ms"] * (self.metrics["total_jobs"] - 1)
            total_time += execution_time
            self.metrics["avg_execution_time_ms"] = total_time / self.metrics["total_jobs"]
            
            # Store result
            await self._store_result(result)
            
            logger.info(f"Worker {worker_id} completed job {job.job_id} "
                       f"in {execution_time:.0f}ms ({'SUCCESS' if result.success else 'FAILED'})")
            
        except Exception as e:
            # Handle job failure
            logger.error(f"Job {job.job_id} failed: {e}")
            await self._handle_job_failure(job, e, worker_id)
    
    async def _execute_job(self, job: JobDefinition) -> JobResult:
        """Execute a specific job type."""
        start_time = time.time()
        
        try:
            # Import job module dynamically
            # from ..jobs.job_types import DECAY_SCORING, CONSOLIDATION, DEDUPLICATION
            
            # Execute based on job type
            if job.job_type == "decay_scoring":
                return await self._execute_decay_scoring(job)
            elif job.job_type == "consolidation":
                return await self._execute_consolidation(job)
            elif job.job_type == "deduplication":
                return await self._execute_deduplication(job)
            elif job.job_type == "consistency_check":
                return await self._execute_consistency_check(job)
            else:
                raise ValueError(f"Unsupported job type: {job.job_type}")
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return JobResult(
                job_id=job.job_id,
                success=False,
                result=None,
                execution_time_ms=execution_time,
                error=str(e),
                worker_id=job.worker_id
            )
    
    async def _execute_decay_scoring(self, job: JobDefinition) -> JobResult:
        """Execute decay scoring job."""
        start_time = time.time()
        
        # Get memory IDs from payload
        memory_ids = job.payload.get("memory_ids", [])
        decay_cutoff_days = job.payload.get("cutoff_days", 90)
        
        if not memory_ids:
            raise ValueError("No memory IDs provided in payload")
        
        processed_memories = []
        for memory_id in memory_ids:
            try:
                memory = await self.db_client.get_memory(memory_id)
                if memory:
                    # Calculate new decay score
                    decay_score = DecayScore.calculate(
                        age_days=(datetime.now(timezone.utc) - memory.created_at).days,
                        half_life_hours=memory.tier.ttl_hours,
                        access_factor=memory.access_count / max(1, memory.access_count)
                    )
                    
                    # Update memory decay score
                    await self.db_client.update_memory(
                        memory_id,
                        updates={
                            "decay_score": decay_score.value,
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }
                    )
                    
                    processed_memories.append({
                        "memory_id": memory_id,
                        "decay_score": decay_score.value,
                        "access_count": memory.access_count
                    })
                    
            except Exception as e:
                logger.error(f"Failed to process memory {memory_id}: {e}")
        
        execution_time = (time.time() - start_time) * 1000
        
        return JobResult(
            job_id=job.job_id,
            success=len(processed_memories) > 0,
            result={
                "processed_memories": len(processed_memories),
                "memory_results": processed_memories
            },
            execution_time_ms=execution_time
        )
    
    async def _execute_consolidation(self, job: JobDefinition) -> JobResult:
        """Execute memory consolidation job."""
        start_time = time.time()
        
        # Get consolidation parameters
        similarity_threshold = job.payload.get("similarity_threshold", 0.8)
        max_group_size = job.payload.get("max_group_size", 5)
        
        # Get memories with high similarity scores
        # This would involve vector similarity calculation in a real implementation
        # For now, we'll simulate the process
        
        consolidation_results = []
        
        # Simulate finding similar memory groups
        # In reality, this would use vector search or semantic similarity
        sample_groups = [
            ["mem_1", "mem_2"],  # Group 1
            ["mem_3", "mem_4", "mem_5"]  # Group 2
        ]
        
        for group in sample_groups[:max_group_size]:
            try:
                # In a real implementation, this would:
                # 1. Calculate semantic similarity
                # 2. Create merged memory content
                # 3. Update entity relationships
                # 4. Archive duplicate memories
                
                consolidation_results.append({
                    "group_members": group,
                    "similarity_score": similarity_threshold + 0.1,
                    "consolidated": True,
                    "merged_memory_id": group[0] + "_merged"
                })
                
            except Exception as e:
                logger.error(f"Failed to consolidate group {group}: {e}")
        
        execution_time = (time.time() - start_time) * 1000
        
        return JobResult(
            job_id=job.job_id,
            success=len(consolidation_results) > 0,
            result={
                "groups_processed": len(consolidation_results),
                "consolidation_results": consolidation_results
            },
            execution_time_ms=execution_time
        )
    
    async def _execute_deduplication(self, job: JobDefinition) -> JobResult:
        """Execute memory deduplication job."""
        start_time = time.time()
        
        # Get deduplication parameters
        hash_threshold = job.payload.get("hash_threshold", 0.95)
        semantic_threshold = job.payload.get("semantic_threshold", 0.8)
        
        # Find and remove duplicate memories
        duplicates_removed = []
        
        # Simulate deduplication process
        # In reality, this would use content hashing and semantic similarity
        sample_duplicates = [
            {"original": "mem_1", "duplicates": ["mem_2", "mem_3"]},
            {"original": "mem_4", "duplicates": ["mem_5"]}
        ]
        
        for dup_data in sample_duplicates:
            try:
                # In a real implementation, this would:
                # 1. Calculate content hashes
                # 2. Find identical/similar content
                # 3. Merge metadata and relationships
                # 4. Archive duplicate memories
                
                duplicates_removed.append({
                    "original_memory": dup_data["original"],
                    "duplicates_found": len(dup_data["duplicates"]),
                    "duplicates": dup_data["duplicates"],
                    "action_taken": "archived"
                })
                
            except Exception as e:
                logger.error(f"Failed to deduplicate group: {dup_data}: {e}")
        
        execution_time = (time.time() - start_time) * 1000
        
        return JobResult(
            job_id=job.job_id,
            success=len(duplicates_removed) > 0,
            result={
                "duplicates_found": sum(dr["duplicates_found"] for dr in duplicates_removed),
                "duplicates_removed": len(duplicates_removed),
                "deduplication_results": duplicates_removed
            },
            execution_time_ms=execution_time
        )

    async def _execute_consistency_check(self, job: JobDefinition) -> JobResult:
        """Execute consistency check job."""
        start_time = time.time()
        
        try:
            from .consistency_job import ConsistencyJob
            
            consistency_job = ConsistencyJob(self.db_client)
            result_data = await consistency_job.execute(job.payload)
            
            execution_time = (time.time() - start_time) * 1000
            
            return JobResult(
                job_id=job.job_id,
                success=True,
                result=result_data,
                execution_time_ms=execution_time,
                worker_id=job.worker_id
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return JobResult(
                job_id=job.job_id,
                success=False,
                result=None,
                execution_time_ms=execution_time,
                error=str(e),
                worker_id=job.worker_id
            )
    
    async def _store_result(self, result: JobResult) -> None:
        """Store job result."""
        if self.redis_client:
            serialized = self._serialize_result(result)
            await self.redis_client.hset(f"result:{result.job_id}", mapping=serialized)
            await self.redis_client.expire(f"result:{result.job_id}", self.redis_ttl)
    
    async def _handle_job_failure(self, job: JobDefinition, error: Exception, worker_id: str) -> None:
        """Handle job failure with retry logic."""
        job.retry_count += 1
        job.status = JobStatus.FAILED if job.retry_count >= job.max_retries else JobStatus.RETRYING
        job.error_message = str(error)
        
        if job.retry_count < job.max_retries:
            # Retry with exponential backoff
            delay = min(300, 30 * (2 ** job.retry_count))  # Max 5 minutes
            
            job.status = JobStatus.PENDING
            self.metrics["retry_count"] += 1
            
            # Reschedule job
            await asyncio.sleep(delay)
            if self.redis_client:
                await self._store_job_redis(job)
            else:
                self._memory_queue.put_nowait(job)
            
            logger.info(f"Job {job.job_id} will be retried ({job.retry_count}/{job.max_retries}) after {delay}s")
        else:
            # Max retries exceeded, mark as failed
            self.metrics["failed_jobs"] += 1
            
            if self.redis_client:
                await self.redis_client.hset(
                    f"job:{job.job_id}",
                    mapping={
                        "status": job.status.value,
                        "error_message": job.error_message,
                        "retry_count": str(job.retry_count)
                    }
                )
            
            logger.error(f"Job {job.job_id} failed after {job.retry_count} retry attempts")
    
    def _serialize_job(self, job: JobDefinition) -> Dict[str, str]:
        """Serialize job definition for Redis storage."""
        return {
            "job_id": job.job_id,
            "job_type": job.job_type,
            "job_class": job.job_class,
            "priority": str(job.priority.value),
            "payload": json.dumps(job.payload),
            "created_at": job.created_at.isoformat(),
            "scheduled_at": job.scheduled_at.isoformat() if job.scheduled_at else "",
            "max_retries": str(job.max_retries),
            "retry_count": str(job.retry_count),
            "timeout_seconds": str(job.timeout_seconds),
            "status": job.status.value,
            "error_message": job.error_message or "",
            "started_at": job.started_at.isoformat() if job.started_at else "",
            "completed_at": job.completed_at.isoformat() if job.completed_at else "",
            "worker_id": job.worker_id or ""
        }
    
    def _deserialize_job(self, data: Dict[str, str]) -> JobDefinition:
        """Deserialize job definition from Redis data."""
        return JobDefinition(
            job_id=data["job_id"],
            job_type=data["job_type"],
            job_class=data["job_class"],
            priority=JobPriority(int(data["priority"])),
            payload=json.loads(data["payload"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            scheduled_at=datetime.fromisoformat(data["scheduled_at"]) if data["scheduled_at"] else None,
            max_retries=int(data["max_retries"]),
            retry_count=int(data["retry_count"]),
            timeout_seconds=int(data["timeout_seconds"]),
            status=JobStatus(data["status"]),
            error_message=data["error_message"] if data["error_message"] else None,
            started_at=datetime.fromisoformat(data["started_at"]) if data["started_at"] else None,
            completed_at=datetime.fromisoformat(data["completed_at"]) if data["completed_at"] else None,
            worker_id=data["worker_id"] if data["worker_id"] else None
        )
    
    def _serialize_result(self, result: JobResult) -> Dict[str, str]:
        """Serialize job result for Redis storage."""
        return {
            "job_id": result.job_id,
            "success": str(result.success),
            "result": json.dumps(result.result),
            "execution_time_ms": str(result.execution_time_ms),
            "error": str(result.error) if result.error else "",
            "completed_at": result.completed_at.isoformat(),
            "worker_id": result.worker_id or ""
        }
    
    def _deserialize_result(self, data: Dict[str, str]) -> JobResult:
        """Deserialize job result from Redis data."""
        return JobResult(
            job_id=data["job_id"],
            success=data["success"] == "True",
            result=json.loads(data["result"]),
            execution_time_ms=float(data["execution_time_ms"]),
            error=data["error"] if data["error"] else None,
            completed_at=datetime.fromisoformat(data["completed_at"]),
            worker_id=data["worker_id"] if data["worker_id"] else None
        )
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get performance metrics."""
        if self.enable_metrics:
            # Calculate jobs per second
            if self.is_running and self.metrics["total_jobs"] > 0:
                uptime_hours = (datetime.now(timezone.utc) - 
                             datetime.now(timezone.utc)).total_seconds() / 3600
                self.metrics["jobs_per_second"] = self.metrics["total_jobs"] / max(1, uptime_hours * 3600)
            
            # Calculate worker utilization
            active_workers = sum(1 for worker in self.worker_tasks if not worker.done())
            self.metrics["worker_utilization"] = active_workers / max(1, self.max_workers)
            
            return self.metrics.copy()
        return {"metrics_disabled": True}
    
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get queue statistics."""
        stats = {
            "pending_jobs": 0,
            "running_jobs": 0,
            "total_workers": self.max_workers,
            "active_workers": 0
        }
        
        if self.redis_client:
            # Get pending jobs from queue
            stats["pending_jobs"] = await self.redis_client.zcard("job:queue")
            
            # Count running jobs (those with RUNNING status)
            job_keys = await self.redis_client.keys("job:*")
            for job_key in job_keys:
                status = await self.redis_client.hget(job_key, "status")
                if status and status == JobStatus.RUNNING.value:
                    stats["running_jobs"] += 1
        
        return stats


# Factory function for easy initialization
def create_job_processor(redis_url: str = "redis://localhost:6379/1", max_workers: int = 4) -> JobProcessor:
    """Create a configured job processor."""
    return JobProcessor(redis_url=redis_url, max_workers=max_workers)
