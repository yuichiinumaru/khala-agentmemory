import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone, timedelta

from khala.application.services.monitoring_service import MonitoringService
from khala.infrastructure.monitoring.metrics_repository import MetricsRepository
from khala.infrastructure.persistence.audit_repository import AuditRepository
from khala.domain.monitoring.entities import GraphSnapshot, SystemMetric
from khala.domain.audit.entities import AuditLog
from khala.infrastructure.surrealdb.client import SurrealDBClient

@pytest.fixture
def mock_client():
    client = MagicMock(spec=SurrealDBClient)
    client.get_connection = MagicMock()
    conn = AsyncMock()
    client.get_connection.return_value.__aenter__.return_value = conn
    return client

@pytest.fixture
def mock_metrics_repo(mock_client):
    repo = MetricsRepository(mock_client)
    repo.save_snapshot = AsyncMock()
    repo.save_metric = AsyncMock()
    repo.get_snapshots = AsyncMock()
    repo.get_metrics = AsyncMock()
    return repo

@pytest.mark.asyncio
async def test_capture_graph_snapshot(mock_client, mock_metrics_repo):
    service = MonitoringService(mock_metrics_repo, mock_client)

    # Mock DB counts
    # First call: node count, Second call: edge count
    conn = mock_client.get_connection.return_value.__aenter__.return_value
    conn.query.side_effect = [
        [{"result": [{"count": 10}], "status": "OK"}],
        [{"result": [{"count": 20}], "status": "OK"}]
    ]

    snapshot = await service.capture_graph_snapshot()

    assert snapshot.node_count == 10
    assert snapshot.edge_count == 20
    # Avg degree = 2 * 20 / 10 = 4.0
    assert snapshot.avg_degree == 4.0
    # Density = 2 * 20 / (10 * 9) = 40 / 90 = 0.444...
    assert 0.44 < snapshot.density < 0.45

    mock_metrics_repo.save_snapshot.assert_called_once()

@pytest.mark.asyncio
async def test_record_system_metric(mock_client, mock_metrics_repo):
    service = MonitoringService(mock_metrics_repo, mock_client)

    metric = await service.record_system_metric("latency", 123.4, {"agent": "A"})

    assert metric.metric_name == "latency"
    assert metric.value == 123.4
    assert metric.labels["agent"] == "A"

    mock_metrics_repo.save_metric.assert_called_once()

@pytest.mark.asyncio
async def test_audit_repository_timeline(mock_client):
    repo = AuditRepository(mock_client)

    conn = mock_client.get_connection.return_value.__aenter__.return_value
    conn.query.return_value = [{"result": [
        {
            "id": "log1",
            "user_id": "u1",
            "operation": "create",
            "target_id": "m1",
            "target_type": "memory",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "agent_id": "agentA",
            "details": {}
        }
    ], "status": "OK"}]

    timeline = await repo.get_agent_timeline("agentA")

    assert len(timeline) == 1
    assert timeline[0].agent_id == "agentA"
    assert timeline[0].operation == "create"
    assert timeline[0].action == "create" # Should fallback to operation
