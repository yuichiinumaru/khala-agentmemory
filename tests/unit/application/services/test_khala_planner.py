import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from khala.application.services.planning_service import PlanningService, Worker
from khala.application.services.planning_utils import parse_step

class MockWorker(Worker):
    async def hint(self):
        return "I do things."
    async def handle(self, param, ctx):
        return f"Done: {param}"

class TestKhalaPlanner(unittest.TestCase):
    def setUp(self):
        self.mock_gemini = MagicMock()
        self.mock_gemini.generate_text = AsyncMock()
        self.workers = [MockWorker()]
        self.planner = PlanningService(self.mock_gemini, self.workers)

    def test_parse_step(self):
        step_text = """
        Goal: Analyze user request.
        <tasks>
        <subtask>
        result_1 = subtask(agent_0, "Check memory")
        </subtask>
        </tasks>
        """
        goal, expressions = parse_step(step_text)
        self.assertEqual(goal, "Goal: Analyze user request.")
        self.assertEqual(len(expressions), 1)
        self.assertEqual(expressions[0]["agent_id"], "agent_0")

    def test_planner_loop_logic(self):
        # Mock Gemini to return a plan then nothing (to stop loop)
        self.mock_gemini.generate_text.side_effect = [
            {"content": """<tasks><subtask>res1 = subtask(agent_0, 'do it')</subtask></tasks>"""},
            {"content": "No more tasks"}
        ]

        import asyncio
        result = asyncio.run(self.planner.run_iterative_plan("Test Instruction"))

        self.assertIn("Finished or Stalled", result)
        self.assertEqual(self.mock_gemini.generate_text.call_count, 2)

if __name__ == "__main__":
    unittest.main()
