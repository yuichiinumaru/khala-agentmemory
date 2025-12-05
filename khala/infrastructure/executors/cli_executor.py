"""CLI Subagent Executor.

This module provides a secure execution environment for external CLI tools.
It enforces strict path validation, resource limits, and absolute binary resolution
to prevent RCE and DoS attacks.
"""

import asyncio
import json
import os
import logging
import tempfile
import time
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

from ...application.orchestration.executor import SubagentExecutor
from ...application.orchestration.types import SubagentTask, SubagentResult, SubagentRole, ModelTier

logger = logging.getLogger(__name__)

# Constants for Resource Limits
MAX_OUTPUT_BYTES = 10 * 1024 * 1024  # 10 MB limit for stdout/stderr
EXECUTION_TIMEOUT_BUFFER = 5  # Seconds to wait for cleanup

class CLISubagentExecutor(SubagentExecutor):
    """
    Executes subagent tasks using the external 'gemini-mcp-tool' CLI.
    Enforces strict security boundaries.
    """
    
    def __init__(self):
        self._npx_path = self._resolve_npx()

    def _resolve_npx(self) -> str:
        """Resolve absolute path to npx binary."""
        npx_path = shutil.which("npx")
        if not npx_path:
            raise RuntimeError(
                "CRITICAL: 'npx' binary not found in system PATH. "
                "Cannot execute external agents safely."
            )
        return npx_path

    def _get_agent_file(self, role: SubagentRole) -> Path:
        """Get path to agent configuration file with Path Traversal Protection."""
        base_env = os.getenv("KHALA_AGENTS_PATH")

        if not base_env:
            # Fallback only if strictly defined in a safe location, else raise
            # For now, we fail loud as per 'Zero Trust'
            raise ValueError(
                "CRITICAL: KHALA_AGENTS_PATH environment variable is not set. "
                "Implicit relative paths are forbidden."
            )

        base_path = Path(base_env).resolve()

        if not base_path.exists() or not base_path.is_dir():
             raise ValueError(f"KHALA_AGENTS_PATH is invalid or not a directory: {base_path}")

        agent_files = {
            SubagentRole.ANALYZER: "research-analyst.md",
            SubagentRole.SYNTHESIZER: "knowledge-synthesizer.md",
            SubagentRole.CURATOR: "code-quality-reviewer.md",
            SubagentRole.RESEARCHER: "research-analyst.md",
            SubagentRole.VALIDATOR: "test-coverage-reviewer.md",
            SubagentRole.CONSOLIDATOR: "knowledge-synthesizer.md",
            SubagentRole.EXTRACTOR: "data-analyst.md",
            SubagentRole.OPTIMIZER: "performance-reviewer.md"
        }

        filename = agent_files.get(role, "research-analyst.md")
        agent_path = (base_path / filename).resolve()

        # Guard: Path Traversal Check
        if not str(agent_path).startswith(str(base_path)):
             raise ValueError(f"Security Alert: Path traversal attempted for agent file: {agent_path}")

        if not agent_path.exists():
             raise FileNotFoundError(f"Agent configuration file not found: {agent_path}")

        return agent_path

    def _get_model_for_tier(self, tier: ModelTier) -> str:
        """Resolve model name from tier."""
        if tier == ModelTier.FAST:
            return "gemini-2.5-flash"
        elif tier == ModelTier.REASONING:
            return "gemini-2.5-pro" 
        else:
            return "gemini-2.5-pro"

    async def _read_stream_safe(self, stream: asyncio.StreamReader) -> str:
        """Read from stream with strict size limits to prevent DoS."""
        output = []
        total_bytes = 0

        while True:
            try:
                chunk = await stream.read(4096)
                if not chunk:
                    break

                total_bytes += len(chunk)
                if total_bytes > MAX_OUTPUT_BYTES:
                    raise RuntimeError(
                        f"DoS Protection: Subprocess output exceeded {MAX_OUTPUT_BYTES} bytes."
                    )

                output.append(chunk.decode(errors='replace'))
            except Exception as e:
                logger.error(f"Stream read error: {e}")
                break

        return "".join(output)

    async def execute_task(self, task: SubagentTask, agent_config: Dict[str, Any]) -> SubagentResult:
        start_time = time.time()
        
        try:
            agent_file = self._get_agent_file(task.role)

            # Prepare temporary workspace
            with tempfile.TemporaryDirectory() as workspace:
                workspace_path = Path(workspace)
                
                # Create task input file
                input_file = workspace_path / "task_input.json"
                with open(input_file, 'w') as f:
                    task_data = {
                        "task": {
                            "id": task.task_id,
                            "type": task.task_type,
                            "role": task.role.value,
                            "priority": task.priority.name
                        },
                        "input": task.input_data,
                        "context": task.context,
                        "expected_output": task.expected_output,
                        "timestamp": task.created_at.isoformat()
                    }
                    json.dump(task_data, f, indent=2, default=str)
                
                model_name = self._get_model_for_tier(task.model_tier)
                
                # Execute Gemini CLI subagent
                # Security: Use absolute path for npx
                cmd = [
                    self._npx_path, "gemini-mcp-tool",
                    "--agent", str(agent_file),
                    "--task", str(input_file),
                    "--model", model_name, 
                    "--temperature", str(agent_config.get("temperature", 0.7)),
                    "--timeout", str(task.timeout_seconds)
                ]
                
                process = await asyncio.create_subprocess_exec(
                    *cmd,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    cwd=str(workspace_path)
                )
                
                # Wait for completion with timeout and capture output securely
                stdout_str = ""
                stderr_str = ""

                try:
                    # Parallel read of stdout and stderr
                    stdout_task = asyncio.create_task(self._read_stream_safe(process.stdout))
                    stderr_task = asyncio.create_task(self._read_stream_safe(process.stderr))

                    await asyncio.wait_for(process.wait(), timeout=task.timeout_seconds)

                    stdout_str = await stdout_task
                    stderr_str = await stderr_task

                    if process.returncode != 0:
                        logger.error(f"Subagent CLI failed (Exit {process.returncode}): {stderr_str}")

                except asyncio.TimeoutError:
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    raise TimeoutError(f"Task {task.task_id} timed out after {task.timeout_seconds}s")
                except RuntimeError as e:
                    # DoS protection triggered
                    try:
                        process.kill()
                    except ProcessLookupError:
                        pass
                    raise e
                
                # Read output
                output_file = workspace_path / "task_output.json"
                execution_time = (time.time() - start_time) * 1000

                if output_file.exists():
                    with open(output_file, 'r') as f:
                        output_data = json.load(f)
                    
                    return SubagentResult(
                        task_id=task.task_id,
                        role=task.role,
                        success=process.returncode == 0,
                        output=output_data.get("output"),
                        reasoning=output_data.get("reasoning", ""),
                        confidence_score=float(output_data.get("confidence", 0.8)),
                        execution_time_ms=execution_time,
                        metadata=task.input_data,
                        error=output_data.get("error") if process.returncode != 0 else None
                    )
                else:
                    return SubagentResult(
                        task_id=task.task_id,
                        role=task.role,
                        success=False,
                        output=None,
                        reasoning="No output file generated",
                        confidence_score=0.0,
                        execution_time_ms=execution_time,
                        error=f"Missing output file. Stderr: {stderr_str}",
                        metadata=task.input_data
                    )
        
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return SubagentResult(
                task_id=task.task_id,
                role=task.role,
                success=False,
                output=None,
                reasoning=f"Execution failed: {str(e)}",
                confidence_score=0.0,
                execution_time_ms=execution_time,
                error=str(e),
                metadata=task.input_data
            )
