from typing import Dict, Any, Optional
import logging
import asyncio
import sys
import io
import os
import traceback
from contextlib import redirect_stdout, redirect_stderr

logger = logging.getLogger(__name__)

class ExecutionEvaluator:
    """
    Service for executing code snippets to evaluate their correctness.
    Strategy 40: Execution-Based Evaluation.

    WARNING: sandbox execution is risky. In a real production system,
    this must be done in an isolated container (e.g., Docker, Firecracker).
    Here we implement a basic restricted execution for demonstration.
    """

    def __init__(self):
        pass

    async def evaluate_code(self, code: str, language: str = "python", timeout: int = 5) -> Dict[str, Any]:
        """
        Execute the provided code and return the output/result.

        SECURITY WARNING: This implementation is a placeholder mock for development.
        Real code execution requires a sandboxed environment (e.g., Docker, Firecracker).
        Executing arbitrary code in the main process is extremely dangerous.

        To enable this feature for TESTING ONLY, set ALLOW_UNSAFE_EVAL=1 environment variable.
        Otherwise it raises NotImplementedError.
        """
        if os.environ.get("ALLOW_UNSAFE_EVAL") != "1":
            raise NotImplementedError(
                "Unsafe code execution is disabled. "
                "Set ALLOW_UNSAFE_EVAL=1 to enable for development/testing, "
                "or implement a real sandbox (Docker/Firecracker)."
            )

        logger.warning("Code execution requested. Using INSECURE development placeholder.")

        if language.lower() != "python":
            return {
                "success": False,
                "error": f"Language {language} not supported for execution."
            }

        # Stricter safety checks for dev mock
        forbidden = ["import", "open", "eval", "exec", "__", "sys", "os", "subprocess", "compile"]
        for term in forbidden:
            if term in code:
                return {
                    "success": False,
                    "error": f"Security violation: code contains forbidden term '{term}'. Sandboxed execution is required for this code."
                }

        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()

        try:
            # Using exec in a restricted scope
            # We strictly limit builtins
            safe_builtins = {
                "print": print,
                "range": range,
                "len": len,
                "int": int,
                "float": float,
                "str": str,
                "list": list,
                "dict": dict,
                "set": set,
                "tuple": tuple,
                "sum": sum,
                "min": min,
                "max": max,
                "abs": abs
            }

            local_scope = {}

            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, {"__builtins__": safe_builtins}, local_scope)

            output = stdout_capture.getvalue()
            error_output = stderr_capture.getvalue()

            return {
                "success": True,
                "output": output,
                "error_output": error_output,
                "variables": {k: str(v) for k, v in local_scope.items() if not k.startswith("__")}
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": traceback.format_exc()
            }
