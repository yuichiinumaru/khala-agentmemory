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
from ....domain.memory.services import MemoryService
from ....application.services.temporal_analyzer import TemporalAnalysisService
from ...surrealdb.client import SurrealDBClient, SurrealConfig
from khala.application.utils import json_serializer

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
        """Initialize job processor."""
        self.redis_url = redis_url
        self.max_workers = max_workers
        self.redis_ttl = redis_ttl_seconds
        self.enable_metrics = enable_metrics
        
        self.redis_client: Optional[redis.Redis] = None
        self._memory_queue: Queue[JobDefinition] = Queue()
        self._memory_jobs: Dict[str, JobDefinition] = {}
        self._memory_results: Dict[str, JobResult] = {}
        
        self.worker_tasks: List[Task] = []
        self.worker_counter = 0
        self.is_running = False
        self._job_classes = {}
        
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
        
        self.memory_service = None
        self.db_client = None
        self.gemini_client = None
        
        self._register_default_jobs()
    
    async def start(self) -> None:
        """Start the job processor."""
        if self.is_running:
            return
        
        try:
            if redis is not None:
                self.redis_client = redis.Redis.from_url(self.redis_url, decode_responses=True)
                await self.redis_client.ping()
                logger.info(f"Connected to Redis at {self.redis_url}")
            else:
                logger.warning("Redis not available, using in-memory queue only")
                self.redis_client = None
            
            # Initialize SurrealDB with strict config
            self.db_client = SurrealDBClient()

            self.memory_service = MemoryService()
            
            try:
                from ...gemini.client import GeminiClient
                self.gemini_client = GeminiClient(enable_cascading=False)
            except Exception as e:
                logger.warning(f"GeminiClient init failed: {e}. Jobs requiring AI will fail.")

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
        
        self.is_running = False
        for worker_task in self.worker_tasks:
            worker_task.cancel()
        
        await asyncio.gather(*self.worker_tasks, return_exceptions=True)
        self.worker_tasks.clear()
        
        if self.redis_client:
            await self.redis_client.close()
        
        if self.db_client:
            await self.db_client.close()

        logger.info("Job processor stopped")
    
    def _register_default_jobs(self) -> None:
        self._job_classes = {
            "decay_scoring": "DecayScoringJob",
            "consolidation": "ConsolidationJob", 
            "deduplication": "DeduplicationJob",
            "consistency_check": "ConsistencyJob",
            "index_repair": "IndexRepairJob",
            "pattern_recognition": "PatternRecognitionJob"
        }
    
    async def submit_job(self, job_type: str, payload: Dict[str, Any], priority: JobPriority = JobPriority.MEDIUM, **kwargs) -> str:
        """Submit a job for processing."""
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
            **kwargs
        )
        
        if self.redis_client:
            await self._store_job_redis(job)
        else:
            self._memory_queue.put_nowait(job)
        
        self.metrics["total_jobs"] += 1
        self.metrics["jobs_by_priority"][priority.value] += 1
        return job_id
    
    async def get_job_status(self, job_id: str) -> Optional[JobDefinition]:
        if self.redis_client:
            job_data = await self.redis_client.hgetall(f"job:{job_id}")
            if job_data: return self._deserialize_job(job_data)
        elif job_id in self._memory_jobs:
            return self._memory_jobs[job_id]
        return None
    
    async def get_job_result(self, job_id: str) -> Optional[JobResult]:
        if self.redis_client:
            result_data = await self.redis_client.hgetall(f"result:{job_id}")
            if result_data: return self._deserialize_result(result_data)
        elif job_id in self._memory_results:
            return self._memory_results[job_id]
        return None
    
    async def _store_job_redis(self, job: JobDefinition) -> None:
        if not self.redis_client:
            self._memory_jobs[job.job_id] = job
            return
        
        serialized = self._serialize_job(job)
        await self.redis_client.hset(f"job:{job.job_id}", mapping=serialized)
        
        score = int(job.priority.value * 1000 - job.created_at.timestamp())
        await self.redis_client.zadd("job:queue", {f"job:{job.job_id}": score})
        
        await self.redis_client.expire(f"job:{job.job_id}", self.redis_ttl)
        await self.redis_client.expire("job:queue", self.redis_ttl)
    
    async def _get_next_job(self) -> Optional[JobDefinition]:
        if self.redis_client:
            result = await self.redis_client.zpopmin("job:queue")
            if result:
                job_key, _ = result[0]
                job_data = await self.redis_client.hgetall(job_key)
                if job_data: return self._deserialize_job(job_data)
        
        if not self._memory_queue.empty():
            return self._memory_queue.get_nowait()
        return None
    
    async def _worker_loop(self, worker_id: str) -> None:
        """Main worker loop with reduced latency."""
        logger.info(f"Worker {worker_id} started")
        
        while self.is_running:
            try:
                job = await self._get_next_job()
                
                if job:
                    await self._process_job(job, worker_id)
                else:
                    # Optimized sleep: 0.1s for responsiveness
                    await asyncio.sleep(0.1)
                    
            except Exception as e:
                logger.error(f"Worker {worker_id} error: {e}")
                # Backoff on error
                await asyncio.sleep(1.0)
        
        logger.info(f"Worker {worker_id} stopped")
    
    async def _process_job(self, job: JobDefinition, worker_id: str) -> None:
        start_time = time.time()
        try:
            job.status = JobStatus.RUNNING
            job.started_at = datetime.now(timezone.utc)
            job.worker_id = worker_id
            
            if self.redis_client:
                await self.redis_client.hset(f"job:{job.job_id}", mapping={"status": job.status.value, "started_at": job.started_at.isoformat(), "worker_id": worker_id})
            else:
                self._memory_jobs[job.job_id] = job
            
            result = await self._execute_job(job)
            
            execution_time = (time.time() - start_time) * 1000
            if result.success:
                self.metrics["successful_jobs"] += 1
            else:
                self.metrics["failed_jobs"] += 1
            
            await self._store_result(result)
            
        except Exception as e:
            logger.error(f"Job {job.job_id} processing failed: {e}")
            await self._handle_job_failure(job, e, worker_id)
    
    async def _execute_job(self, job: JobDefinition) -> JobResult:
        start_time = time.time()
        try:
            if job.job_type == "decay_scoring": return await self._execute_decay_scoring(job)
            elif job.job_type == "consolidation": return await self._execute_consolidation(job)
            elif job.job_type == "deduplication": return await self._execute_deduplication(job)
            elif job.job_type == "consistency_check": return await self._execute_consistency_check(job)
            elif job.job_type == "index_repair": return await self._execute_index_repair(job)
            elif job.job_type == "pattern_recognition": return await self._execute_pattern_recognition(job)
            else: raise ValueError(f"Unsupported job type: {job.job_type}")
        except Exception as e:
            return JobResult(job.job_id, False, None, (time.time() - start_time) * 1000, str(e), worker_id=job.worker_id)
    
    async def _execute_decay_scoring(self, job: JobDefinition) -> JobResult:
        start_time = time.time()
        memory_ids = job.payload.get("memory_ids", [])
        
        if not memory_ids and job.payload.get("scan_all", False):
            # OOM Protection: Limit scan to 5000 items
            query = "SELECT id FROM memory WHERE is_archived = false LIMIT 5000;"
            async with self.db_client.get_connection() as conn:
                response = await conn.query(query)
                if response and isinstance(response, list):
                    items = response[0].get('result', response) if len(response) > 0 and isinstance(response[0], dict) else response
                    memory_ids = [str(item['id']).split(':')[1] if ':' in str(item['id']) else str(item['id']) for item in items]

        if not memory_ids:
             return JobResult(job.job_id, True, {"processed": 0}, (time.time() - start_time) * 1000)
        
        temporal_service = TemporalAnalysisService(self.db_client)
        results = await temporal_service.batch_process_decay(memory_ids)
        return JobResult(job.job_id, results["processed"] > 0, results, (time.time() - start_time) * 1000)
    
    async def _execute_consolidation(self, job: JobDefinition) -> JobResult:
        start_time = time.time()
        user_id = job.payload.get("user_id")
        processed_count = 0
        
        from khala.application.services.memory_lifecycle import MemoryLifecycleService
        from khala.infrastructure.persistence.surrealdb_repository import SurrealDBMemoryRepository
        
        repo = SurrealDBMemoryRepository(self.db_client)
        lifecycle_service = MemoryLifecycleService(repository=repo, gemini_client=self.gemini_client)
        
        users = [user_id] if user_id else []
        if not users and job.payload.get("scan_all"):
             query = "SELECT user_id FROM memory GROUP BY user_id LIMIT 100;"
             async with self.db_client.get_connection() as conn:
                response = await conn.query(query)
                if response and isinstance(response, list):
                    items = response[0].get('result', response) if len(response) > 0 and isinstance(response[0], dict) else response
                    users = [item['user_id'] for item in items if 'user_id' in item]

        for uid in users:
            try:
                count = await lifecycle_service.consolidate_memories(uid)
                processed_count += count
            except Exception as e:
                logger.error(f"Consolidation failed for {uid}: {e}")
        
        return JobResult(job.job_id, True, {"processed": processed_count}, (time.time() - start_time) * 1000)

    async def _execute_deduplication(self, job): return JobResult(job.job_id, True, {"status": "not_implemented"}, 0)
    async def _execute_consistency_check(self, job): return JobResult(job.job_id, True, {"status": "not_implemented"}, 0)
    async def _execute_index_repair(self, job): return JobResult(job.job_id, True, {"status": "not_implemented"}, 0)
    async def _execute_pattern_recognition(self, job): return JobResult(job.job_id, True, {"status": "not_implemented"}, 0)

    async def _store_result(self, result: JobResult) -> None:
        if self.redis_client:
            serialized = self._serialize_result(result)
            await self.redis_client.hset(f"result:{result.job_id}", mapping=serialized)
            await self.redis_client.expire(f"result:{result.job_id}", self.redis_ttl)
    
    async def _handle_job_failure(self, job: JobDefinition, error: Exception, worker_id: str) -> None:
        job.retry_count += 1
        job.status = JobStatus.FAILED if job.retry_count >= job.max_retries else JobStatus.RETRYING
        job.error_message = str(error)
        
        if job.retry_count < job.max_retries:
            delay = min(300, 30 * (2 ** job.retry_count))
            job.status = JobStatus.PENDING
            job.scheduled_at = datetime.now(timezone.utc) + timedelta(seconds=delay)
            self.metrics["retry_count"] += 1
            if self.redis_client: await self._store_job_redis(job)
            else: asyncio.create_task(self._requeue_delayed(job, delay))
            logger.info(f"Job {job.job_id} rescheduled for retry in {delay}s")
        else:
            self.metrics["failed_jobs"] += 1
            if self.redis_client:
                await self.redis_client.hset(f"job:{job.job_id}", mapping={"status": job.status.value, "error_message": job.error_message})
            logger.error(f"Job {job.job_id} failed permanently")

    async def _requeue_delayed(self, job, delay):
        await asyncio.sleep(delay)
        self._memory_queue.put_nowait(job)

    def _serialize_job(self, job: JobDefinition) -> Dict[str, str]:
        return {
            "job_id": job.job_id, "job_type": job.job_type, "job_class": job.job_class,
            "priority": str(job.priority.value),
            "payload": json.dumps(job.payload, default=json_serializer), # FIX: Safe Serialization
            "created_at": job.created_at.isoformat(), "max_retries": str(job.max_retries),
            "retry_count": str(job.retry_count), "timeout_seconds": str(job.timeout_seconds),
            "status": job.status.value
        }
    
    def _deserialize_job(self, data: Dict[str, str]) -> JobDefinition:
        return JobDefinition(
            job_id=data["job_id"], job_type=data["job_type"], job_class=data["job_class"],
            priority=JobPriority(int(data["priority"])), payload=json.loads(data["payload"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            max_retries=int(data["max_retries"]), retry_count=int(data["retry_count"]),
            timeout_seconds=int(data["timeout_seconds"]), status=JobStatus(data["status"])
        )

    def _serialize_result(self, result: JobResult) -> Dict[str, str]:
        return {
            "job_id": result.job_id, "success": str(result.success),
            "result": json.dumps(result.result, default=json_serializer), # FIX: Safe Serialization
            "execution_time_ms": str(result.execution_time_ms),
            "completed_at": result.completed_at.isoformat()
        }

    def _deserialize_result(self, data: Dict[str, str]) -> JobResult:
        return JobResult(
            job_id=data["job_id"], success=data["success"] == "True",
            result=json.loads(data["result"]), execution_time_ms=float(data["execution_time_ms"]),
            completed_at=datetime.fromisoformat(data["completed_at"])
        )

    async def get_metrics(self) -> Dict[str, Any]:
        return self.metrics.copy() if self.enable_metrics else {}

    async def get_queue_stats(self) -> Dict[str, Any]:
        return {"pending_jobs": self._memory_queue.qsize()} # Simplified for memory queue

def create_job_processor(redis_url: str = "redis://localhost:6379/1", max_workers: int = 4) -> JobProcessor:
    return JobProcessor(redis_url=redis_url, max_workers=max_workers)
