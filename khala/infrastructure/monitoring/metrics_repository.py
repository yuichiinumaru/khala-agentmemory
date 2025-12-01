"""Metrics repository implementation."""
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from khala.domain.monitoring.entities import GraphSnapshot, SystemMetric
from khala.infrastructure.surrealdb.client import SurrealDBClient

logger = logging.getLogger(__name__)

class MetricsRepository:
    """Repository for storing monitoring metrics."""

    def __init__(self, client: SurrealDBClient):
        self.client = client

    async def save_snapshot(self, snapshot: GraphSnapshot) -> str:
        """Save a graph snapshot."""
        query = """
        CREATE type::thing('graph_snapshot', $id) CONTENT {
            timestamp: $timestamp,
            node_count: $node_count,
            edge_count: $edge_count,
            avg_degree: $avg_degree,
            density: $density,
            metadata: $metadata
        };
        """
        params = snapshot.to_dict()

        try:
            async with self.client.get_connection() as conn:
                await conn.query(query, params)
            return snapshot.id
        except Exception as e:
            logger.error(f"Failed to save graph snapshot: {e}")
            raise

    async def get_snapshots(self, start_time: datetime, end_time: datetime) -> List[GraphSnapshot]:
        """Retrieve graph snapshots within a time range."""
        query = """
        SELECT * FROM graph_snapshot
        WHERE timestamp >= $start_time AND timestamp <= $end_time
        ORDER BY timestamp ASC;
        """
        params = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        try:
            async with self.client.get_connection() as conn:
                result = await conn.query(query, params)

                rows = []
                if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
                    rows = result[0]['result']

                snapshots = []
                for row in rows:
                    ts_str = row['timestamp']
                    # Handle Z suffix
                    if ts_str.endswith('Z'):
                        ts_str = ts_str[:-1] + '+00:00'

                    snapshots.append(GraphSnapshot(
                        id=row['id'],
                        timestamp=datetime.fromisoformat(ts_str),
                        node_count=row['node_count'],
                        edge_count=row['edge_count'],
                        avg_degree=row['avg_degree'],
                        density=row['density'],
                        metadata=row.get('metadata', {})
                    ))
                return snapshots
        except Exception as e:
            logger.error(f"Failed to get snapshots: {e}")
            return []

    async def save_metric(self, metric: SystemMetric) -> str:
        """Save a system metric."""
        query = """
        CREATE type::thing('system_metric', $id) CONTENT {
            timestamp: $timestamp,
            metric_name: $metric_name,
            value: $value,
            labels: $labels
        };
        """
        params = metric.to_dict()

        try:
            async with self.client.get_connection() as conn:
                await conn.query(query, params)
            return metric.id
        except Exception as e:
            logger.error(f"Failed to save metric: {e}")
            raise

    async def get_metrics(self, metric_name: str, start_time: datetime, end_time: datetime) -> List[SystemMetric]:
        """Retrieve metrics by name and time range."""
        query = """
        SELECT * FROM system_metric
        WHERE metric_name = $metric_name
        AND timestamp >= $start_time
        AND timestamp <= $end_time
        ORDER BY timestamp ASC;
        """
        params = {
            "metric_name": metric_name,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        try:
            async with self.client.get_connection() as conn:
                result = await conn.query(query, params)

                rows = []
                if isinstance(result, list) and len(result) > 0 and 'result' in result[0]:
                    rows = result[0]['result']

                metrics = []
                for row in rows:
                    ts_str = row['timestamp']
                    if ts_str.endswith('Z'):
                        ts_str = ts_str[:-1] + '+00:00'

                    metrics.append(SystemMetric(
                        id=row['id'],
                        timestamp=datetime.fromisoformat(ts_str),
                        metric_name=row['metric_name'],
                        value=row['value'],
                        labels=row.get('labels', {})
                    ))
                return metrics
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []
