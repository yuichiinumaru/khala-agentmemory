"""Unit tests for InstructionRepository."""

import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from khala.domain.instruction.entities import Instruction, InstructionSet, InstructionType
from khala.infrastructure.persistence.instruction_repository import SurrealDBInstructionRepository

@pytest.fixture
def mock_client():
    client = AsyncMock()
    connection = AsyncMock()

    # Mock connection methods to return data immediately (not awaitable unless we make them so)
    # The actual implementation calls await conn.query(...).
    # AsyncMock handles this automatically.

    # We need client.get_connection() to be a synchronous call that returns an async context manager.
    # OR if it's an async method (it's decorated with @asynccontextmanager in implementation),
    # it returns an async generator.

    # The implementation uses @asynccontextmanager
    # async def get_connection(self): ... yield connection

    # So when we call client.get_connection(), it returns an async context manager.

    class MockAsyncContextManager:
        async def __aenter__(self):
            return connection
        async def __aexit__(self, exc_type, exc, tb):
            pass

    # IMPORTANT: The method itself is NOT async in the mock definition unless side_effect is set.
    # But if we just set return_value, it's fine for a standard method.
    # However, if the code calls `async with client.get_connection() as conn`,
    # client.get_connection() must return the CM.

    # Since client is an AsyncMock, all its methods are AsyncMocks by default.
    # An AsyncMock, when called, returns a coroutine.
    # But `get_connection` is used in `async with`.
    # `async with await client.get_connection()` would be valid if it returned a coroutine that returned a CM.
    # But standard usage `async with client.get_connection()` expects the call to return the CM directly (not awaitable).

    # So we need to treat `get_connection` as a MagicMock (standard mock) that returns the CM,
    # NOT an AsyncMock.

    client.get_connection = MagicMock(return_value=MockAsyncContextManager())

    return client

@pytest.fixture
def repository(mock_client):
    return SurrealDBInstructionRepository(mock_client)

@pytest.mark.asyncio
async def test_create_instruction(repository, mock_client):
    instruction = Instruction(
        id="test-inst",
        name="Test Prompt",
        content="You are a helpful assistant.",
        instruction_type=InstructionType.SYSTEM,
        version="1.0.0"
    )

    # Mock DB response
    # Since we replaced the return_value with our AsyncContextManager class,
    # we need to access the 'connection' object we created in the fixture.
    # However, since that's inside the fixture, we can get it by calling the method
    # and entering the context (which we can't easily do here without refactoring fixture).
    # A cleaner way is to mock the connection methods directly on the object returned by __aenter__

    # Let's inspect what get_connection returns
    ctx = mock_client.get_connection()
    mock_connection = await ctx.__aenter__()

    mock_connection.query.return_value = [{
        "result": [{
            "id": "instruction:test-inst",
            "name": "Test Prompt",
            "content": "You are a helpful assistant.",
            "instruction_type": "system",
            "version": "1.0.0",
            "is_active": True,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }]
    }]

    result = await repository.create_instruction(instruction)

    assert result.id == "test-inst"
    assert result.name == "Test Prompt"
    assert result.instruction_type == InstructionType.SYSTEM

    mock_connection.query.assert_called_once()
    args, _ = mock_connection.query.call_args
    assert "CREATE instruction:test-inst" in args[0]

@pytest.mark.asyncio
async def test_get_instruction(repository, mock_client):
    # Mock DB response
    ctx = mock_client.get_connection()
    mock_connection = await ctx.__aenter__()

    mock_connection.select.return_value = {
        "id": "instruction:test-inst",
        "name": "Test Prompt",
        "content": "You are a helpful assistant.",
        "instruction_type": "system",
        "version": "1.0.0",
        "is_active": True
    }

    result = await repository.get_instruction("test-inst")

    assert result is not None
    assert result.id == "test-inst"
    assert result.name == "Test Prompt"

    mock_connection.select.assert_called_once_with("instruction:test-inst")

@pytest.mark.asyncio
async def test_get_instruction_by_name(repository, mock_client):
    # Mock DB response
    ctx = mock_client.get_connection()
    mock_connection = await ctx.__aenter__()

    mock_connection.query.return_value = [{
        "result": [{
            "id": "instruction:test-inst",
            "name": "Test Prompt",
            "content": "You are a helpful assistant.",
            "instruction_type": "system",
            "version": "1.0.0",
            "is_active": True
        }]
    }]

    result = await repository.get_instruction_by_name("Test Prompt")

    assert result is not None
    assert result.name == "Test Prompt"

    mock_connection.query.assert_called_once()
    args, _ = mock_connection.query.call_args
    assert "WHERE name = $name" in args[0]
    # Check the second argument which is the params dict
    assert args[1]['name'] == "Test Prompt"

@pytest.mark.asyncio
async def test_create_instruction_set(repository, mock_client):
    inst1 = Instruction(id="i1", name="I1", content="C1", instruction_type=InstructionType.SYSTEM)
    inst_set = InstructionSet(
        id="set1",
        name="Set 1",
        description="Desc",
        instructions=[inst1]
    )

    ctx = mock_client.get_connection()
    mock_connection = await ctx.__aenter__()

    # Mock create response
    mock_connection.query.side_effect = [
        # First call: create
        [{
            "result": [{
                "id": "instruction_set:set1",
                # ... other fields
            }]
        }],
        # Second call: fetch
        [{
            "result": [{
                "id": "instruction_set:set1",
                "name": "Set 1",
                "description": "Desc",
                "instructions": [{
                    "id": "instruction:i1",
                    "name": "I1",
                    "content": "C1",
                    "instruction_type": "system",
                    "is_active": True
                }]
            }]
        }]
    ]

    result = await repository.create_instruction_set(inst_set)

    assert result.id == "set1"
    assert len(result.instructions) == 1
    assert result.instructions[0].id == "i1"
    assert mock_connection.query.call_count == 2
