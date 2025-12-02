"""Job for executing index repair logic."""

from typing import Dict, Any
import logging

from typing import Optional
from .job_processor import JobResult
from khala.application.services.index_repair_service import IndexRepairService
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.gemini.client import GeminiClient

logger = logging.getLogger(__name__)

class IndexRepairJob:
    """Job to run the Index Repair Service."""

    def __init__(self, db_client: SurrealDBClient, gemini_client: Optional[GeminiClient] = None):
        """Initialize the job.

        Args:
            db_client: SurrealDB client
            gemini_client: Gemini client (optional, will create if None)
        """
        self.db_client = db_client
        self.gemini_client = gemini_client or GeminiClient()
        self.service = IndexRepairService(self.db_client, self.gemini_client)

    async def execute(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the repair job.

        Args:
            payload: Job parameters (fix, batch_size, scan_all)

        Returns:
            Job result data
        """
        fix = payload.get("fix", True)
        batch_size = payload.get("batch_size", 50)
        scan_all = payload.get("scan_all", False)

        logger.info(f"Starting Index Repair Job (fix={fix}, batch={batch_size})")

        report = await self.service.scan_and_repair(
            fix=fix,
            batch_size=batch_size,
            scan_all=scan_all
        )

        logger.info(f"Index Repair Job completed: {report}")
        return report
