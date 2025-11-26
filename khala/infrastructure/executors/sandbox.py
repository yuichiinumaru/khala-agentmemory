"""Sandbox executor for running untrusted code."""

import logging
import asyncio
import tempfile
import os
import sys
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class SandboxExecutor:
    """
    Executes code in a isolated subprocess.
    WARNING: This is not a security boundary. For production, use Docker/Firecracker.
    """
    
    async def execute_python(
        self, 
        code: str, 
        timeout_seconds: int = 5,
        env_vars: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Execute Python code string in a subprocess.
        """
        # Create a temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            temp_path = f.name
            
        try:
            # Prepare environment
            env = os.environ.copy()
            if env_vars:
                env.update(env_vars)
                
            # Run the process
            proc = await asyncio.create_subprocess_exec(
                sys.executable, temp_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout_seconds)
                
                return {
                    "success": proc.returncode == 0,
                    "stdout": stdout.decode().strip(),
                    "stderr": stderr.decode().strip(),
                    "return_code": proc.returncode,
                    "timeout": False
                }
                
            except asyncio.TimeoutError:
                proc.kill()
                return {
                    "success": False,
                    "stdout": "",
                    "stderr": "Execution timed out",
                    "return_code": -1,
                    "timeout": True
                }
                
        except Exception as e:
            logger.error(f"Sandbox execution error: {e}")
            return {
                "success": False,
                "stdout": "",
                "stderr": str(e),
                "return_code": -1,
                "timeout": False
            }
            
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)
