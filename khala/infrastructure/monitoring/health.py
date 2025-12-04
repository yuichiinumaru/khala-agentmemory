"""System health monitoring."""

import logging
import asyncio
from typing import Dict, Any, Optional
from datetime import datetime, timezone

from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient
from khala.infrastructure.background.jobs.job_processor import JobProcessor

logger = logging.getLogger(__name__)

class HealthMonitor:
    """Monitor system health and component status."""
    
    def __init__(
        self,
        db_client: SurrealDBClient,
        gemini_client: GeminiClient,
        job_processor: Optional[JobProcessor] = None
    ):
        self.db_client = db_client
        self.gemini_client = gemini_client
        self.job_processor = job_processor
        
    async def check_health(self) -> Dict[str, Any]:
        """Perform a full system health check."""
        status = {
            "status": "healthy",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "components": {}
        }
        
        # Check Database
        try:
            # Simple query to check connection
            async with self.db_client.get_connection() as conn:
                await conn.query("RETURN true;")
            status["components"]["database"] = {"status": "up"}
        except Exception as e:
            status["components"]["database"] = {"status": "down", "error": str(e)}
            status["status"] = "degraded"
            
        # Check Gemini
        try:
            # Check if models are initialized
            if self.gemini_client._models:
                cache_stats = self.gemini_client.get_cache_stats()
                status["components"]["llm"] = {
                    "status": "up",
                    "models": list(self.gemini_client._models.keys()),
                    "cache_stats": cache_stats
                }
            else:
                status["components"]["llm"] = {"status": "unknown", "details": "No models initialized"}
        except Exception as e:
            status["components"]["llm"] = {"status": "down", "error": str(e)}
            status["status"] = "degraded"
            
        # Check Job Processor
        if self.job_processor:
            try:
                queue_stats = await self.job_processor.get_queue_stats()
                status["components"]["job_processor"] = {
                    "status": "up",
                    "queue_depth": queue_stats.get("pending_jobs", 0),
                    "active_workers": queue_stats.get("active_workers", 0)
                }
            except Exception as e:
                status["components"]["job_processor"] = {"status": "down", "error": str(e)}
                status["status"] = "degraded"

        return status
