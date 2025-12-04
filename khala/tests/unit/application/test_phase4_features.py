
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime, timezone, timedelta
import networkx as nx

from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore, Relationship
from khala.domain.memory.repository import MemoryRepository
from khala.domain.graph.service import GraphService
from khala.application.services.activity_analysis_service import ActivityAnalysisService
from khala.application.services.adaptive_learning_service import AdaptiveLearningService
from khala.application.services.memory_lifecycle import MemoryLifecycleService
from khala.infrastructure.persistence.audit_repository import AuditRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient

class TestPhase4Features(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        # Mocks
        self.memory_repo = MagicMock(spec=MemoryRepository)
        self.memory_repo.client = MagicMock()
        self.audit_repo = MagicMock(spec=AuditRepository)
        self.audit_repo.client = MagicMock()
        self.db_client = MagicMock(spec=SurrealDBClient)

        # Services
        self.graph_service = GraphService(self.memory_repo)
        self.activity_service = ActivityAnalysisService(self.audit_repo)
        self.adaptive_service = AdaptiveLearningService(self.db_client)
        self.lifecycle_service = MemoryLifecycleService(
            repository=self.memory_repo,
            gemini_client=MagicMock()
        )

    # Strategy 41, 75, 119: Graph Tests
    async def test_bitemporal_relationship(self):
        # Mock client create
        self.memory_repo.client.create_relationship = AsyncMock()

        rel_id = await self.graph_service.create_bitemporal_relationship(
            "e1", "e2", "related", strength=0.8
        )
        self.memory_repo.client.create_relationship.assert_called_once()
        args = self.memory_repo.client.create_relationship.call_args[0][0]
        self.assertIsInstance(args, Relationship)
        self.assertEqual(args.relation_type, "related")
        self.assertIsNotNone(args.valid_from)

    async def test_invalidate_relationship(self):
        # Mock client query
        self.memory_repo.client.get_connection.return_value.__aenter__.return_value.query = AsyncMock()

        success = await self.graph_service.invalidate_relationship("rel1")
        self.assertTrue(success)
        self.memory_repo.client.get_connection.return_value.__aenter__.return_value.query.assert_called_once()
        # Verify query sets valid_to
        call_args = self.memory_repo.client.get_connection.return_value.__aenter__.return_value.query.call_args
        self.assertIn("UPDATE relationship SET valid_to", call_args[0][0])

    async def test_graph_snapshot(self):
        # Mock client response
        mock_response = [{'result': [
            {'from_entity_id': 'e1', 'to_entity_id': 'e2', 'relation_type': 'A', 'strength': 1.0},
            {'from_entity_id': 'e2', 'to_entity_id': 'e3', 'relation_type': 'B', 'strength': 0.5}
        ], 'status': 'OK'}]

        self.memory_repo.client.get_connection.return_value.__aenter__.return_value.query = AsyncMock(return_value=mock_response)

        snapshot = await self.graph_service.get_graph_snapshot(datetime.now(timezone.utc))

        self.assertIsInstance(snapshot, nx.DiGraph)
        self.assertEqual(snapshot.number_of_nodes(), 3)
        self.assertEqual(snapshot.number_of_edges(), 2)

    # Strategy 104: Activity Tests
    async def test_agent_timeline(self):
        mock_response = [{'result': [
            {'timestamp': '2023-01-01T12:00:00Z', 'operation': 'op1'},
            {'timestamp': '2023-01-01T13:00:00Z', 'operation': 'op2'}
        ], 'status': 'OK'}]
        self.audit_repo.client.get_connection.return_value.__aenter__.return_value.query = AsyncMock(return_value=mock_response)

        timeline = await self.activity_service.get_agent_timeline("agent1")
        self.assertEqual(len(timeline), 2)
        self.assertEqual(timeline[0]['operation'], 'op1')

    # Strategy 106: Consolidation Schedule
    async def test_consolidation_schedule(self):
        # Mock memory accumulation
        self.memory_repo.get_by_tier = AsyncMock(return_value=[MagicMock() for _ in range(60)]) # > 50 trigger

        # Mock consolidation
        self.lifecycle_service.consolidate_memories = AsyncMock(return_value=5)

        result = await self.lifecycle_service.schedule_consolidation("user1")

        self.assertEqual(result["status"], "executed")
        self.assertEqual(result["reason"], "volume_threshold_exceeded")
        self.lifecycle_service.consolidate_memories.assert_called_once()

    # Strategy 108: Learning Curve
    async def test_learning_curve(self):
        self.db_client.get_connection.return_value.__aenter__.return_value.query = AsyncMock()

        await self.adaptive_service.track_learning_curve("m1", 1, 0.5, 0.8, 1.0)

        # Verify query
        call_args = self.db_client.get_connection.return_value.__aenter__.return_value.query.call_args
        self.assertIn("CREATE training_curves", call_args[0][0])
