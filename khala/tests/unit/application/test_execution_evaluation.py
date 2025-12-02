"""Unit tests for ExecutionEvaluationService."""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime

from khala.application.services.execution_evaluation import ExecutionEvaluationService
from khala.infrastructure.executors.sandbox import SandboxExecutor
from khala.domain.memory.entities import Memory

@pytest.fixture
def mock_sandbox():
    sandbox = MagicMock(spec=SandboxExecutor)
    sandbox.execute_python = AsyncMock()
    return sandbox

@pytest.fixture
def service(mock_sandbox):
    return ExecutionEvaluationService(sandbox=mock_sandbox)

@pytest.mark.asyncio
async def test_evaluate_code_success(service, mock_sandbox):
    code = "print('hello')"
    mock_sandbox.execute_python.return_value = {
        "success": True,
        "stdout": "hello",
        "stderr": "",
        "return_code": 0,
        "timeout": False
    }

    result = await service.evaluate_code(code)

    assert result["success"] is True
    assert result["stdout"] == "hello"
    mock_sandbox.execute_python.assert_called_once_with(code=code, timeout_seconds=5, env_vars=None)

@pytest.mark.asyncio
async def test_evaluate_code_unsupported_language(service):
    with pytest.raises(ValueError, match="Unsupported language"):
        await service.evaluate_code("print('hello')", language="java")

@pytest.mark.asyncio
async def test_evaluate_memory_success(service, mock_sandbox):
    memory = Memory(
        id="mem1",
        content="```python\nprint(1+1)\n```",
        user_id="user1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tier="working",
        importance=0.5,
        tags=[]
    )

    mock_sandbox.execute_python.return_value = {
        "success": True,
        "stdout": "2",
        "stderr": "",
        "return_code": 0,
        "timeout": False
    }

    result = await service.evaluate_memory(memory)

    assert result["execution"]["success"] is True
    assert result["execution"]["stdout"] == "2"
    assert result["suggested_updates"]["verification_status"] == "verified"

    # Verify code extraction logic
    mock_sandbox.execute_python.assert_called_once()
    args = mock_sandbox.execute_python.call_args
    assert args.kwargs['code'] == "print(1+1)"

@pytest.mark.asyncio
async def test_evaluate_memory_failure(service, mock_sandbox):
    memory = Memory(
        id="mem2",
        content="x = 1 / 0",
        user_id="user1",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        tier="working",
        importance=0.5,
        tags=[]
    )

    mock_sandbox.execute_python.return_value = {
        "success": False,
        "stdout": "",
        "stderr": "ZeroDivisionError",
        "return_code": 1,
        "timeout": False
    }

    result = await service.evaluate_memory(memory)

    assert result["execution"]["success"] is False
    assert result["suggested_updates"]["verification_status"] == "failed"
    assert "ZeroDivisionError" in result["suggested_updates"]["verification_issues"]
