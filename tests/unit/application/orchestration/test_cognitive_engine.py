import unittest
from unittest.mock import MagicMock, AsyncMock, patch
import asyncio
from khala.application.orchestration.cognitive_engine import CognitiveEngine, BaseEvent, EventInput, ReturnBehavior
from khala.infrastructure.persistence.audit_repository import AuditRepository
from khala.infrastructure.surrealdb.client import SurrealDBClient

class TestCognitiveEngine(unittest.TestCase):
    def setUp(self):
        self.mock_client = MagicMock(spec=SurrealDBClient)
        self.mock_repo = MagicMock(spec=AuditRepository)
        self.mock_repo.log = AsyncMock()
        self.engine = CognitiveEngine(name="test_engine", client=self.mock_client, audit_repo=self.mock_repo)

    def test_make_event(self):
        async def sample_task(inp, ctx):
            return "done"

        event = self.engine.make_event(sample_task)
        self.assertIsInstance(event, BaseEvent)
        self.assertEqual(event.id, self.engine.get_event_from_id(event.id).id)

    def test_engine_reset(self):
        async def task(inp, ctx): return "ok"
        event = self.engine.make_event(task)
        self.assertIsNotNone(self.engine.get_event_from_id(event.id))
        self.engine.reset()
        self.assertIsNone(self.engine.get_event_from_id(event.id))

    def test_invoke_event_simple(self):
        async def task(inp, ctx):
            return f"processed {inp.results.get('input')}"

        event = self.engine.make_event(task)
        initial_input = EventInput(group_name="start", results={"input": "data"})

        result = asyncio.run(self.engine.invoke_event(event, initial_input))

        self.assertIn(event.id, result)
        self.assertEqual(result[event.id]["result"], "processed data")

    def test_dag_execution(self):
        # A -> B
        async def task_a(inp, ctx):
            return "A"

        async def task_b(inp, ctx):
            # Input from A comes in results
            data_from_a = list(inp.results.values())[0]
            return f"B got {data_from_a}"

        event_a = self.engine.make_event(task_a)

        # B listens to A
        @self.engine.listen_group([event_a])
        async def wrapped_b(inp, ctx):
            return await task_b(inp, ctx)

        event_b = self.engine.get_event_from_id(wrapped_b.id)

        initial_input = EventInput(group_name="start", results={})
        result = asyncio.run(self.engine.invoke_event(event_a, initial_input))

        self.assertIn(event_a.id, result)
        self.assertIn(event_b.id, result)
        self.assertEqual(result[event_b.id]["result"], "B got A")

    def test_audit_logging(self):
        async def task(inp, ctx): return "audit_me"
        event = self.engine.make_event(task)
        asyncio.run(self.engine.invoke_event(event, EventInput(group_name="start", results={})))

        # Verify broker logic logged the start/end of cycle
        # Note: The broker logic implementation is inside invoke_event usually or wraps it.
        # Check if audit_repo.log was called.
        self.assertTrue(self.mock_repo.log.called)

if __name__ == "__main__":
    unittest.main()
