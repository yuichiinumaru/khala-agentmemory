"""Monitoring Service for KHALA.

Implements strategies:
- 75. Temporal Graph Evolution
- 105. System Metrics Time-Series
"""
import logging
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

from khala.domain.monitoring.entities import GraphSnapshot, SystemMetric
from khala.infrastructure.monitoring.metrics_repository import MetricsRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class MonitoringService:
    """Service for monitoring system health and graph evolution."""

    def __init__(self, metrics_repo: MetricsRepository, db_client: SurrealDBClient):
        self.metrics_repo = metrics_repo
        self.db_client = db_client

    async def capture_graph_snapshot(self) -> GraphSnapshot:
        """Capture a snapshot of the current graph metrics.

        Calculates:
        - Node count (Entity table)
        - Edge count (Relationship table)
        - Average degree
        - Density
        """
        try:
            # We need to execute queries to get counts
            # Since client methods might not expose direct count queries, we use raw query

            async with self.db_client.get_connection() as conn:
                # Get node count
                node_res = await conn.query("SELECT count() FROM entity GROUP ALL;")
                node_count = 0
                # Parsing SurrealDB response can be tricky depending on version/client
                # Usually: [{'result': [{'count': 123}], 'status': 'OK'}]
                if isinstance(node_res, list) and len(node_res) > 0:
                    result_part = node_res[0].get('result', [])
                    if result_part and len(result_part) > 0:
                        node_count = result_part[0].get('count', 0)

                # Get edge count
                edge_res = await conn.query("SELECT count() FROM relationship GROUP ALL;")
                edge_count = 0
                if isinstance(edge_res, list) and len(edge_res) > 0:
                    result_part = edge_res[0].get('result', [])
                    if result_part and len(result_part) > 0:
                        edge_count = result_part[0].get('count', 0)

            # Calculate metrics
            avg_degree = 0.0
            density = 0.0

            if node_count > 0:
                avg_degree = (edge_count * 2) / node_count
                if node_count > 1:
                    density = (edge_count * 2) / (node_count * (node_count - 1))

            snapshot = GraphSnapshot(
                node_count=node_count,
                edge_count=edge_count,
                avg_degree=avg_degree,
                density=density,
                metadata={}
            )

            await self.metrics_repo.save_snapshot(snapshot)
            logger.info(f"Captured graph snapshot: {snapshot.id}")
            return snapshot

        except Exception as e:
            logger.error(f"Failed to capture graph snapshot: {e}")
            raise

    async def record_system_metric(self, name: str, value: float, labels: Dict[str, str] = None) -> SystemMetric:
        """Record a system metric."""
        metric = SystemMetric(
            metric_name=name,
            value=value,
            labels=labels or {}
        )
        await self.metrics_repo.save_metric(metric)
        return metric

    async def get_graph_evolution(self, start_time: datetime, end_time: datetime) -> List[GraphSnapshot]:
        """Get graph evolution over time."""
        return await self.metrics_repo.get_snapshots(start_time, end_time)

    async def get_system_metrics(self, name: str, start_time: datetime, end_time: datetime) -> List[SystemMetric]:
        """Get system metrics over time."""
        return await self.metrics_repo.get_metrics(name, start_time, end_time)
