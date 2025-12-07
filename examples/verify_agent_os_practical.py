import asyncio
import logging
import uuid
import sys
from datetime import datetime, timezone

# Add repo root to path
sys.path.append(".")

from khala.application.orchestration.gemini_subagent_system import GeminiSubagentSystem
from khala.application.orchestration.types import SubagentTask, SubagentRole, TaskPriority, SubagentResult
from khala.application.orchestration.executor import SubagentExecutor
from typing import Dict, Any

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AgentOS_Verify")

# Mock Executor for Practical Test without external dependencies
class PracticalMockExecutor(SubagentExecutor):
    async def execute_task(self, task: SubagentTask, agent_config: Dict[str, Any]) -> SubagentResult:
        logger.info(f"Executing task {task.task_id} with role {task.role.value}")
        await asyncio.sleep(0.1) # Simulate work

        # Simulate intelligent response based on task type
        output = f"Processed {task.task_type} for {task.task_id}"
        reasoning = f"Reasoning for {task.role.value}: Valid input."

        if task.task_type == "memory_analysis":
             output = "Analysis: Memory contains high-value conceptual information regarding 'Agent OS'."
             reasoning = "Analyzed content keywords and structure."

        return SubagentResult(
            task_id=task.task_id,
            role=task.role,
            success=True,
            output=output,
            reasoning=reasoning,
            confidence_score=0.95,
            execution_time_ms=100,
            metadata=task.input_data
        )

async def main():
    logger.info("Starting Agent OS Practical Verification...")

    # Initialize System with Mock Executor
    executor = PracticalMockExecutor()
    system = GeminiSubagentSystem(max_concurrent_agents=4, executor=executor)

    # Define a complex task: Memory Analysis Batch
    logger.info("Submitting batch analysis task...")

    # Create fake memories
    from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
    memories = [
        Memory(id="mem1", content="Agent OS is crucial for Khala.", user_id="u1", tier=MemoryTier.WORKING, importance=ImportanceScore(0.9)),
        Memory(id="mem2", content="Verification logic must be robust.", user_id="u1", tier=MemoryTier.WORKING, importance=ImportanceScore(0.8))
    ]

    # Run analysis
    results = await system.analyze_memory_batch(memories)

    logger.info(f"Received {len(results)} results.")

    # Evaluate Results
    for res in results:
        logger.info(f"Task {res.task_id} ({res.role.value}): Success={res.success}")
        logger.info(f"Output: {res.output}")
        logger.info(f"Reasoning: {res.reasoning}")

        if not res.success or "Analysis" not in res.output:
            logger.error("Evaluation Failed: Unexpected output or failure.")
            sys.exit(1)

    logger.info("Agent OS Practical Test: PASSED")

if __name__ == "__main__":
    asyncio.run(main())
