import asyncio
import logging
from typing import List, Dict, Any

from mcp.server.fastmcp import FastMCP
from khala.interface.mcp.khala_subagent_tools import KHALASubagentTools
from khala.infrastructure.surrealdb.client import SurrealDBClient
from khala.infrastructure.persistence.surrealdb_repository import SurrealDBMemoryRepository
import os

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize FastMCP server
mcp = FastMCP("Khala Memory Server")

# Initialize Tools
try:
    # Configuration from environment
    SURREAL_URL = os.getenv("SURREAL_URL", "ws://localhost:8000/rpc")
    SURREAL_USER = os.getenv("SURREAL_USER", "root")
    SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
    SURREAL_NS = os.getenv("SURREAL_NS", "khala")
    SURREAL_DB = os.getenv("SURREAL_DB", "memories")

    # Initialize Persistence
    db_client = SurrealDBClient(
        url=SURREAL_URL,
        username=SURREAL_USER,
        password=SURREAL_PASS,
        namespace=SURREAL_NS,
        database=SURREAL_DB
    )
    repository = SurrealDBMemoryRepository(db_client)
    
    # Initialize Tools with Repository
    khala_tools = KHALASubagentTools(repository=repository)
    logger.info("KHALASubagentTools initialized successfully with SurrealDB persistence.")
except Exception as e:
    logger.error(f"Failed to initialize KHALASubagentTools: {e}")
    raise

@mcp.tool()
async def analyze_memories(memory_data_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Analyze multiple memories in parallel using Gemini subagents.
    
    Args:
        memory_data_list: List of dicts containing 'content', 'user_id', 'tier', 'importance'.
    """
    return await khala_tools.analyze_memories_parallel(memory_data_list)

@mcp.tool()
async def extract_entities(memory_contents: List[str]) -> Dict[str, Any]:
    """
    Extract entities from multiple memory texts in parallel.
    
    Args:
        memory_contents: List of text strings to extract entities from.
    """
    return await khala_tools.extract_entities_batch(memory_contents)

@mcp.tool()
async def consolidate_memories(memory_groups: List[List[Dict[str, Any]]]) -> Dict[str, Any]:
    """
    Intelligently consolidate similar memories using subagent analysis.
    
    Args:
        memory_groups: List of lists, where each inner list is a group of similar memory dicts.
    """
    return await khala_tools.consolidate_memories_smart(memory_groups)

@mcp.tool()
async def verify_memories(memory_list: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Comprehensive multi-agent verification of memories.
    
    Args:
        memory_list: List of memory dicts to verify.
    """
    return await khala_tools.verify_memories_comprehensive(memory_list)

@mcp.tool()
async def get_status() -> Dict[str, Any]:
    """Get current status and performance metrics of the Khala system."""
    return await khala_tools.get_system_status()

@mcp.tool()
async def save_memory(memory_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save a memory to the SurrealDB repository.
    
    Args:
        memory_data: Dict containing 'content' (required), 'user_id', 'tier', 'importance', 'tags', 'category', 'metadata'.
    """
    return await khala_tools.save_memory(memory_data)

@mcp.tool()
async def search_memories(query: str, user_id: str = "mcp_user", limit: int = 5) -> Dict[str, Any]:
    """
    Search memories using text search (BM25).
    
    Args:
        query: Search query string.
        user_id: ID of the user to search memories for.
        limit: Max number of results.
    """
    return await khala_tools.search_memories(query, user_id, limit)

if __name__ == "__main__":
    mcp.run()
