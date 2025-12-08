import pytest
import asyncio
import os
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock

from khala.infrastructure.executors.cli_executor import CLISubagentExecutor, MAX_OUTPUT_BYTES
from khala.application.orchestration.types import SubagentRole

@pytest.fixture
def executor():
    with patch("shutil.which", return_value="/usr/bin/npx"):
        return CLISubagentExecutor()

@pytest.mark.asyncio
async def test_rce_path_resolution(executor):
    """Test that paths are resolved correctly and safely."""
    with tempfile.TemporaryDirectory() as tmpdir:
        agents_dir = Path(tmpdir) / "agents"
        agents_dir.mkdir()

        # Create a valid agent file
        (agents_dir / "research-analyst.md").touch()

        with patch.dict(os.environ, {"KHALA_AGENTS_PATH": str(agents_dir)}):
            # Test valid access
            # We map ANALYZER -> research-analyst.md
            path = executor._get_agent_file(SubagentRole.ANALYZER)
            assert path == agents_dir / "research-analyst.md"

            # Test existence check
            # OPTIMIZER -> performance-reviewer.md (not created)
            with pytest.raises(FileNotFoundError):
                executor._get_agent_file(SubagentRole.OPTIMIZER)

@pytest.mark.asyncio
async def test_dos_protection(executor):
    """Test that reading large streams triggers error."""
    stream = AsyncMock()

    # Create chunks that sum up to > MAX_OUTPUT_BYTES
    chunk_size = 1024 * 1024 # 1MB
    chunks = [b"x" * chunk_size] * 11 # 11MB > 10MB
    chunks.append(b"") # End of stream

    stream.read.side_effect = chunks

    with pytest.raises(RuntimeError, match="DoS Protection"):
        await executor._read_stream_safe(stream)

@pytest.mark.asyncio
async def test_resolve_npx_security(executor):
    """Test npx resolution security."""
    # Already mocked in fixture, but let's verify logic
    # If shutil.which returns None, it should raise
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="CRITICAL"):
             executor._resolve_npx()
