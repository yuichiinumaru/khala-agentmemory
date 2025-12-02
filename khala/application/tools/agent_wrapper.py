from typing import Any, Dict, Optional, Type
from pydantic import BaseModel
from .base import AgentTool
from ...infrastructure.executors.cli_executor import CLISubagentExecutor
from ...application.orchestration.types import SubagentTask, SubagentRole, ModelTier
from datetime import datetime, timezone
import uuid

class ExternalAgentTool(AgentTool):
    """
    Wrapper to call an external agent as a tool.
    Uses CLISubagentExecutor to run the agent.
    """

    def __init__(
        self,
        role: SubagentRole,
        name: str,
        description: str,
        executor: Optional[CLISubagentExecutor] = None,
        args_schema: Optional[Type[BaseModel]] = None
    ):
        super().__init__(name, description, args_schema)
        self.role = role
        self.executor = executor or CLISubagentExecutor()

    async def run(self, input_data: Optional[Dict[str, Any]] = None, context: Optional[Dict[str, Any]] = None, **kwargs) -> Dict[str, Any]:
        """
        Run the external agent.

        Args:
            input_data: The input data for the agent task.
            context: Optional context dictionary.
            **kwargs: Additional arguments.
        """
        # If input_data is None, try to construct it from kwargs
        if input_data is None:
            input_data = kwargs
        else:
            # Merge kwargs into input_data
            input_data.update(kwargs)

        # Validate input if schema is present
        # Note: input_data itself might be the kwargs if unpacked, but here we treat it as a single dict
        # The args_schema usually defines what "input_data" should look like.

        if self.args_schema:
            # If input_data is a dict, we validate it against schema
            # If kwargs contains the fields of schema, we use kwargs
            # For simplicity, we assume input_data matches schema fields
            try:
                self.args_schema(**input_data)
            except Exception as e:
                 raise ValueError(f"Invalid input data for agent {self.name}: {e}")

        task = SubagentTask(
            task_id=str(uuid.uuid4()),
            task_type="tool_execution",
            role=self.role,
            priority=kwargs.get("priority", "medium"), # This likely needs to be an enum if strict
            input_data=input_data,
            context=context or {},
            expected_output=kwargs.get("expected_output", "result"),
            created_at=datetime.now(timezone.utc),
            model_tier=kwargs.get("model_tier", ModelTier.BALANCED),
            timeout_seconds=kwargs.get("timeout_seconds", 60)
        )

        # Determine agent config
        agent_config = {
            "temperature": kwargs.get("temperature", 0.7)
        }

        result = await self.executor.execute_task(task, agent_config)

        if not result.success:
            raise RuntimeError(f"Agent execution failed: {result.error}")

        return {
            "output": result.output,
            "reasoning": result.reasoning,
            "confidence": result.confidence_score,
            "metadata": {
                "execution_time_ms": result.execution_time_ms
            }
        }
