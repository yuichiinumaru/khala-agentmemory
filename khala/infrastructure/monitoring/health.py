"""System health monitoring."""

import logging
import asyncio
from typing import Dict, Any
from datetime import datetime, timezone

from typing import Optional
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
                status["components"]["llm"] = {"status": "up", "models": list(self.gemini_client._models.keys())}
            else:
                status["components"]["llm"] = {"status": "unknown", "details": "No models initialized"}
        except Exception as e:
            status["components"]["llm"] = {"status": "down", "error": str(e)}
            status["status"] = "degraded"

        # Check Job Queue (Task 106: System Load)
        if self.job_processor:
            try:
                stats = await self.job_processor.get_queue_stats()
                pending = stats.get("pending_jobs", 0)
                running = stats.get("running_jobs", 0)

                # Simple load heuristic: if queue > 100, consider degraded/busy
                if pending > 100:
                    status["components"]["queue"] = {"status": "busy", "pending": pending}
                    status["status"] = "degraded"
                else:
                    status["components"]["queue"] = {"status": "ok", "pending": pending, "running": running}
            except Exception as e:
                status["components"]["queue"] = {"status": "unknown", "error": str(e)}

        return status
