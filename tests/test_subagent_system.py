import pytest
import asyncio
from unittest.mock import MagicMock, patch
from datetime import datetime, timezone
from typing import Dict, Any

from khala.application.orchestration.gemini_subagent_system import GeminiSubagentSystem
from khala.application.orchestration.types import (
    SubagentTask, 
    SubagentRole, 
    TaskPriority,
    SubagentResult,
    ModelTier
)
from khala.application.orchestration.executor import SubagentExecutor
from khala.domain.memory.entities import Memory, MemoryTier
from khala.domain.memory.value_objects import ImportanceScore

# Mock Executor
class MockSubagentExecutor(SubagentExecutor):
    async def execute_task(self, task: SubagentTask, agent_config: Dict[str, Any]) -> SubagentResult:
        # Return a dummy result
        return SubagentResult(
            task_id=task.task_id,
            role=task.role,
            success=True,
            output="Mock Output",
            reasoning="Mock Reasoning",
            confidence_score=0.9,
            execution_time_ms=10,
            metadata=task.input_data
        )

@pytest.fixture
def subagent_system():
    executor = MockSubagentExecutor()
    return GeminiSubagentSystem(max_concurrent_agents=2, executor=executor)

@pytest.mark.asyncio
async def test_submit_task_structure(subagent_system):
    """Test that a task can be submitted and queued correctly."""
    task = SubagentTask(
        task_id="test_task_1",
        role=SubagentRole.ANALYZER,
        priority=TaskPriority.HIGH,
        task_type="test_analysis",
        input_data={"content": "test"},
        context={},
        model_tier=ModelTier.FAST
    )
    
    task_id = await subagent_system.submit_task(task)
    assert task_id == "test_task_1"
    # With the mock executor, it might execute immediately if we await enough
    # But submit_task just appends to queue and triggers processing background task
    # We can check if it's in active or completed
    await asyncio.sleep(0.1) # Give it a moment
    
    status = subagent_system.get_task_status("test_task_1")
    assert status["status"] in ["active", "completed"]

@pytest.mark.asyncio
async def test_verify_memories_consensus_logic(subagent_system):
    """
    Test the consensus logic in verify_memories_with_consensus.
    We mock the internal verify_memories call to return controlled results.
    """
    # Mock memories
    memories = [
        Memory(
            id="mem_1", 
            content="The sky is blue.", 
            user_id="user1", 
            tier=MemoryTier.WORKING, 
            importance=ImportanceScore(0.5)
        )
    ]
    
    # Mock the raw results from verify_memories
    # We simulate 3 agents: 2 success (high conf), 1 failure
    mock_results = [
        SubagentResult(
            task_id="verify_analyzer_mem_1_uuid1",
            role=SubagentRole.ANALYZER,
            success=True,
            output="Confirmed",
            reasoning="Visual check",
            confidence_score=0.9,
            execution_time_ms=100,
            metadata={"memory_id": "mem_1"}
        ),
        SubagentResult(
            task_id="verify_researcher_mem_1_uuid2",
            role=SubagentRole.RESEARCHER,
            success=True,
            output="Confirmed",
            reasoning="Scientific paper",
            confidence_score=0.8,
            execution_time_ms=120,
            metadata={"memory_id": "mem_1"}
        ),
        SubagentResult(
            task_id="verify_curator_mem_1_uuid3",
            role=SubagentRole.CURATOR,
            success=False, # Failed execution
            output=None,
            reasoning="Error",
            confidence_score=0.0,
            execution_time_ms=50,
            error="Timeout",
            metadata={"memory_id": "mem_1"}
        )
    ]
    
    # Patch the instance method directly
    with patch.object(subagent_system, 'verify_memories', return_value=mock_results) as mock_verify:
        report = await subagent_system.verify_memories_with_consensus(memories)
        
        assert report["status"] == "completed"
        assert report["memories_verified"] == 1
        
        mem_result = report["results"]["mem_1"]
        # 2 successful agents. Both > 0.7 confidence.
        # Consensus = 2/2 = 1.0
        assert mem_result["agent_count"] == 2
        assert mem_result["consensus_score"] == 1.0
        assert mem_result["recommendation"] == "accept"

@pytest.mark.asyncio
async def test_executor_integration(subagent_system):
    """Test that the executor is actually called."""
    # We can spy on the executor
    with patch.object(subagent_system.executor, 'execute_task', wraps=subagent_system.executor.execute_task) as mock_execute:
        task = SubagentTask(
            task_id="test_task_exec",
            role=SubagentRole.ANALYZER,
            priority=TaskPriority.HIGH,
            task_type="test_exec",
            input_data={"content": "test"},
            context={}
        )
        
        await subagent_system.submit_task(task)
        await asyncio.sleep(0.1)
        
        mock_execute.assert_called_once()
        # Verify arguments
        args, _ = mock_execute.call_args
        assert args[0].task_id == "test_task_exec"
