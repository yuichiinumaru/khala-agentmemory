from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from dataclasses import dataclass
from datetime import datetime

from .types import SubagentTask, SubagentResult, SubagentRole, ModelTier

class SubagentExecutor(ABC):
    """
    Abstract base class for executing subagent tasks.
    Decouples the orchestration logic from the execution mechanism (CLI, API, Docker).
    """
    
    @abstractmethod
    async def execute_task(self, task: SubagentTask, agent_config: Dict[str, Any]) -> SubagentResult:
        """
        Execute a single task.
        
        Args:
            task: The task to execute.
            agent_config: Configuration for the agent (model, temperature, etc).
            
        Returns:
            SubagentResult: The result of the execution.
        """
        pass
