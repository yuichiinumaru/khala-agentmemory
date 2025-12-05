import asyncio
import logging
from typing import List, Dict, Any
import os

from mcp.server.fastmcp import FastMCP
from khala.interface.mcp.khala_subagent_tools import KHALASubagentTools
from khala.infrastructure.surrealdb.client import SurrealDBClient, SurrealConfig
from khala.infrastructure.persistence.surrealdb_repository import SurrealDBMemoryRepository

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Khala Memory Server")

# Initialize Tools
try:
    # "The Rite of Resurrection": Use strict config
    try:
        config = SurrealConfig.from_env()
    except ValueError as e:
        logger.critical(f"Startup Failed: {e}")
        # In a real app we might exit, but FastMCP might need to stay up to report error?
        # No, fail fast.
        raise e

    # Initialize Persistence
    db_client = SurrealDBClient(config)

    # We must ensure initialization happens.
    # Since mcp.run() blocks, we need a startup hook or lazy init.
    # SurrealDBClient does lazy init on get_connection, so it's safe *if* tools use the repository methods.

    repository = SurrealDBMemoryRepository(db_client)
    
    # Initialize Tools with Repository
    khala_tools = KHALASubagentTools(repository=repository)
    logger.info("KHALASubagentTools initialized successfully with SurrealDB persistence.")

except Exception as e:
    logger.error(f"Failed to initialize KHALASubagentTools: {e}")
    raise

@mcp.tool()
async def analyze_memories(memory_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Analyze multiple memories in parallel."""
    return await khala_tools.analyze_memories_parallel(memory_data_list)

@mcp.tool()
async def extract_entities(memory_contents: List[str]) -> Dict[str, Any]:
    """Extract entities from multiple memory texts."""
    return await khala_tools.extract_entities_batch(memory_contents)

@mcp.tool()
async def consolidate_memories(memory_groups: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """Intelligently consolidate similar memories."""
    return await khala_tools.consolidate_memories_smart(memory_groups)

@mcp.tool()
async def verify_memories(memory_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Comprehensive multi-agent verification."""
    return await khala_tools.verify_memories_comprehensive(memory_list)

@mcp.tool()
async def get_status() -> Dict[str, Any]:
    """Get current status and performance metrics."""
    return await khala_tools.get_system_status()

@mcp.tool()
async def save_memory(memory_data: Dict[str, Any]) -> Dict[str, Any]:
    """Save a memory to the repository."""
    return await khala_tools.save_memory(memory_data)

@mcp.tool()
async def search_memories(query: str, user_id: str = "mcp_user", limit: int = 5) -> Dict[str, Any]:
    """Search memories using text search."""
    # Note: user_id allows access to any user data.
    # In a real deployment, this must be behind an Auth Gateway.
    return await khala_tools.search_memories(query, user_id, limit)

if __name__ == "__main__":
    mcp.run()
