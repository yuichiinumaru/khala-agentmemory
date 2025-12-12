import unittest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from khala.application.services.worker_adapters import AgnoToolWorker

class MockAgnoTool:
    def __init__(self, name="TestTool", desc="A test tool"):
        self.name = name
        self.description = desc

    def run(self, query: str):
        return f"Processed: {query}"

class MockAsyncAgnoTool:
    def __init__(self, name="AsyncTestTool", desc="An async test tool"):
        self.name = name
        self.description = desc

    async def arun(self, query: str):
        return f"Async Processed: {query}"

class TestWorkerAdapters(unittest.TestCase):
    def test_sync_tool_execution(self):
        tool = MockAgnoTool()
        worker = AgnoToolWorker(tool)

        # Verify hint
        hint = asyncio.run(worker.hint())
        self.assertIn("TestTool", hint)
        self.assertIn("A test tool", hint)

        # Verify execution
        result = asyncio.run(worker.handle("input", {}))
        self.assertEqual(result, "Processed: input")

    def test_async_tool_execution(self):
        tool = MockAsyncAgnoTool()
        worker = AgnoToolWorker(tool)

        result = asyncio.run(worker.handle("input", {}))
        self.assertEqual(result, "Async Processed: input")

    def test_callable_tool(self):
        async def my_func(x): return f"Func: {x}"
        my_func.__doc__ = "Docstring desc"
        # Monkey patch name for the adapter to pick it up cleanly or it defaults
        my_func.name = "MyFunc"

        worker = AgnoToolWorker(my_func)
        # Note: getattr(func, "name", ...) might fail for function objects if not set,
        # but Adapter handles getattr safely.

        result = asyncio.run(worker.handle("input", {}))
        self.assertEqual(result, "Func: input")

if __name__ == "__main__":
    unittest.main()
