"""Service for execution-based evaluation of code."""

import logging
from typing import Dict, Any, Optional, List
from khala.infrastructure.executors.sandbox import SandboxExecutor
from khala.domain.memory.entities import Memory

logger = logging.getLogger(__name__)

class ExecutionEvaluationService:
    """
    Service to execute code snippets and evaluate their correctness.
    Implements Strategy 40: Execution-Based Evaluation.
    """

    def __init__(self, sandbox: SandboxExecutor = None):
        self.sandbox = sandbox or SandboxExecutor()

    async def evaluate_code(
        self,
        code: str,
        language: str = "python",
        timeout: int = 5,
        env_vars: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Execute code and return the result.

        Args:
            code: The code string to execute.
            language: The programming language (currently only 'python').
            timeout: Execution timeout in seconds.
            env_vars: Optional environment variables.

        Returns:
            Dict containing execution results (success, stdout, stderr, etc).
        """
        if language.lower() != "python":
            raise ValueError(f"Unsupported language: {language}")

        logger.info(f"Executing python code snippet (length: {len(code)})")
        result = await self.sandbox.execute_python(
            code=code,
            timeout_seconds=timeout,
            env_vars=env_vars
        )

        return result

    async def evaluate_memory(
        self,
        memory: Memory,
        code_field: str = "content",
        update_verification: bool = True
    ) -> Dict[str, Any]:
        """
        Extract code from a memory and evaluate it.

        Args:
            memory: The memory entity containing code.
            code_field: The field name containing the code (default 'content').
            update_verification: Whether to update memory verification status (requires repo access,
                                 but here we just return the data for the caller to save).

        Returns:
            Dict containing execution results and suggested memory updates.
        """
        # Simple extraction logic: assume the whole content is code
        # or wrapped in ```python ... ``` blocks.
        code = getattr(memory, code_field, "")
        if not code:
            return {"success": False, "error": "No code found in memory"}

        # Basic markdown block cleaning
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()
        elif "```" in code:
            code = code.split("```")[1].split("```")[0].strip()

        result = await self.evaluate_code(code)

        # Prepare updates
        updates = {
            "execution_result": result,
            "verified": result["success"]
        }

        if update_verification:
            if result["success"]:
                updates["verification_status"] = "verified"
                updates["verification_score"] = 1.0
            else:
                updates["verification_status"] = "failed"
                updates["verification_score"] = 0.0
                updates["verification_issues"] = [result["stderr"]]

        return {
            "execution": result,
            "suggested_updates": updates
        }
