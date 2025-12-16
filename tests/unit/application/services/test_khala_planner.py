import pytest
from unittest.mock import AsyncMock, MagicMock
from khala.application.services.khala_planner import KhalaPlanner, PlanStep

@pytest.fixture
def mock_client():
    return AsyncMock()

@pytest.fixture
def planner(mock_client):
    return KhalaPlanner(mock_client)

def test_parse_step_standard(planner):
    text = """
    Thought: I need to search for apples.
    Action: Search
    Args: {"query": "apples"}
    """
    step = planner.parse_step(text)
    assert step.thought == "I need to search for apples."
    assert step.action == "Search"
    assert step.args == {"query": "apples"}

def test_parse_step_no_args(planner):
    text = """
    Thought: Done.
    Action: Finish
    """
    step = planner.parse_step(text)
    assert step.action == "Finish"
    assert step.args == {}

@pytest.mark.asyncio
async def test_execute_loop(planner, mock_client):
    # Mock responses
    mock_client.generate_text.side_effect = [
        {"content": 'Thought: 1\nAction: ToolA\nArgs: {"x": 1}'},
        {"content": 'Thought: 2\nAction: Finish\nArgs: {}'}
    ]

    mock_worker = AsyncMock()
    mock_worker.execute.return_value = "ResultA"

    steps = await planner.execute_task("Do it", mock_worker)

    assert len(steps) == 1 # Only ToolA is stored as a step, Finish breaks loop?
    # Or Finish is also a step? Usually Finish is terminal.
    # In my logic, I break if Action == Finish. So Finish step is not added?
    # Let's verify implementation logic.

    assert steps[0].action == "ToolA"
    assert steps[0].result == "ResultA"
