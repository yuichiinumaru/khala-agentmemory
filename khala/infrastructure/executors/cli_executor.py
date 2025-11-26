import asyncio
import json
import tempfile
import time
from pathlib import Path
from typing import Dict, Any

from ...application.orchestration.executor import SubagentExecutor
from ...application.orchestration.types import SubagentTask, SubagentResult, SubagentRole, ModelTier

class CLISubagentExecutor(SubagentExecutor):
    """
    Executes subagent tasks using the external 'gemini-mcp-tool' CLI.
    """
    
    def _get_agent_file(self, role: SubagentRole) -> Path:
        """Get path to agent configuration file."""
        # TODO: Make this configurable via environment variables or config file
        agent_files = {
            SubagentRole.ANALYZER: "/home/suportesaude/YUICHI/06-NEXUS/.gemini/agents/research-analyst.md",
            SubagentRole.SYNTHESIZER: "/home/suportesaude/YUICHI/06-NEXUS/.gemini/agents/knowledge-synthesizer.md",
            SubagentRole.CURATOR: "/home/suportesaude/YUICHI/06-NEXUS/.gemini/agents/code-quality-reviewer.md",
            SubagentRole.RESEARCHER: "/home/suportesaude/YUICHI/06-NEXUS/.gemini/agents/research-analyst.md",
            SubagentRole.VALIDATOR: "/home/suportesaude/YUICHI/06-NEXUS/.gemini/agents/test-coverage-reviewer.md",
            SubagentRole.CONSOLIDATOR: "/home/suportesaude/YUICHI/06-NEXUS/.gemini/agents/knowledge-synthesizer.md",
            SubagentRole.EXTRACTOR: "/home/suportesaude/YUICHI/06-NEXUS/.gemini/agents/data-analyst.md",
            SubagentRole.OPTIMIZER: "/home/suportesaude/YUICHI/06-NEXUS/.gemini/agents/performance-reviewer.md"
        }
        return agent_files.get(role, agent_files[SubagentRole.ANALYZER])

    def _get_model_for_tier(self, tier: ModelTier) -> str:
        """Resolve model name from tier."""
        if tier == ModelTier.FAST:
            return "gemini-2.5-flash"
        elif tier == ModelTier.REASONING:
            return "gemini-2.5-pro" 
        else:
            return "gemini-2.5-pro"

    async def execute_task(self, task: SubagentTask, agent_config: Dict[str, Any]) -> SubagentResult:
        start_time = time.time()
        
        try:
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
                
                agent_file = self._get_agent_file(task.role)
                model_name = self._get_model_for_tier(task.model_tier)
                
                # Execute Gemini CLI subagent
                cmd = [
                    "npx", "gemini-mcp-tool",
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
                
                # Wait for completion with timeout
                try:
                    stdout, stderr = await asyncio.wait_for(
                        process.wait(),
                        timeout=task.timeout_seconds
                    )
                except asyncio.TimeoutError:
                    process.kill()
                    raise TimeoutError(f"Task {task.task_id} timed out")
                
                # Read output
                output_file = workspace_path / "task_output.json"
                if output_file.exists():
                    with open(output_file, 'r') as f:
                        output_data = json.load(f)
                    
                    execution_time = (time.time() - start_time) * 1000
                    
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
                        execution_time_ms=(time.time() - start_time) * 1000,
                        error="Missing output file",
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
