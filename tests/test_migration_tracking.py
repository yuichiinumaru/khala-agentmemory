import pytest
import pytest_asyncio
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock
from khala.domain.audit.entities import AuditLog
from khala.infrastructure.persistence.audit_repository import AuditRepository
from khala.application.services.migration_tracking_service import MigrationTrackingService

@pytest.mark.asyncio
async def test_migration_tracking_empty():
    mock_repo = AsyncMock(spec=AuditRepository)
    mock_repo.get_logs_by_target.return_value = []

    service = MigrationTrackingService(mock_repo)
    result = await service.track_memory_path("mem1")

    assert result == []

@pytest.mark.asyncio
async def test_migration_tracking_flow():
    mock_repo = AsyncMock(spec=AuditRepository)

    ts1 = datetime(2023, 1, 1, 10, 0, 0, tzinfo=timezone.utc)
    ts2 = datetime(2023, 1, 1, 11, 0, 0, tzinfo=timezone.utc)

    logs = [
        AuditLog(user_id="agent1", action="create", target_id="mem1", target_type="memory", timestamp=ts1),
        AuditLog(user_id="agent2", action="read", target_id="mem1", target_type="memory", timestamp=ts2)
    ]

    mock_repo.get_logs_by_target.return_value = logs

    service = MigrationTrackingService(mock_repo)
    result = await service.track_memory_path("mem1")

    assert len(result) == 2
    assert result[0]["step"] == 1
    assert result[0]["agent_id"] == "agent1"
    assert result[0]["action"] == "create"

    assert result[1]["step"] == 2
    assert result[1]["agent_id"] == "agent2"
    assert result[1]["action"] == "read"
