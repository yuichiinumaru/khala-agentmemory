import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from khala.infrastructure.executors.cli_executor import CLISubagentExecutor

@pytest.mark.asyncio
async def test_resolve_npx_success():
    with patch("shutil.which", return_value="/usr/bin/npx"):
        executor = CLISubagentExecutor()
        assert executor._npx_path == "/usr/bin/npx"

@pytest.mark.asyncio
async def test_resolve_npx_failure():
    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="CRITICAL"):
            CLISubagentExecutor()
