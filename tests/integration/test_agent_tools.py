import pytest
from unittest.mock import AsyncMock, MagicMock
from khala.application.tools.agent_wrapper import ExternalAgentTool
from khala.application.orchestration.types import SubagentRole, SubagentResult
from pydantic import BaseModel

class InputSchema(BaseModel):
    query: str
    limit: int

@pytest.mark.asyncio
async def test_external_agent_tool_success():
    mock_executor = MagicMock()
    mock_executor.execute_task = AsyncMock(return_value=SubagentResult(
        task_id="123",
        role=SubagentRole.RESEARCHER,
        success=True,
        output={"summary": "Found it"},
        reasoning="Looked hard",
        confidence_score=0.95,
        execution_time_ms=100.0,
        metadata={}
    ))

    tool = ExternalAgentTool(
        role=SubagentRole.RESEARCHER,
        name="researcher",
        description="Researches stuff",
        executor=mock_executor,
        args_schema=InputSchema
    )

    result = await tool.run(query="test", limit=5)

    assert result["output"] == {"summary": "Found it"}
    assert result["confidence"] == 0.95

    # Verify executor was called correctly
    args = mock_executor.execute_task.call_args
    task = args[0][0]
    assert task.role == SubagentRole.RESEARCHER
    assert task.input_data == {"query": "test", "limit": 5}

@pytest.mark.asyncio
async def test_external_agent_tool_validation_error():
    tool = ExternalAgentTool(
        role=SubagentRole.RESEARCHER,
        name="researcher",
        description="Researches stuff",
        executor=MagicMock(),
        args_schema=InputSchema
    )

    with pytest.raises(ValueError, match="Invalid input data"):
        # Missing 'limit'
        await tool.run(query="test")
