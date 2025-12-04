from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
import logging
from typing import Dict, Any, AsyncGenerator
from contextlib import asynccontextmanager
import os

from ...infrastructure.surrealdb.client import SurrealDBClient, SurrealConfig
from ...infrastructure.persistence.surrealdb_repository import SurrealDBMemoryRepository
from ...interface.mcp.khala_subagent_tools import KHALASubagentTools

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security
API_KEY_NAME = "X-API-Key"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)

def get_api_key(api_key_header: str = Security(api_key_header)):
    """Validate API Key."""
    expected_key = os.getenv("KHALA_API_KEY")
    if not expected_key:
        # If no key configured, we might allow it in dev, or block.
        # Zero Trust: Block it.
        logger.warning("KHALA_API_KEY not set. Blocking access.")
        raise HTTPException(status_code=500, detail="Server misconfiguration: Auth not set")

    if api_key_header == expected_key:
        return api_key_header
    raise HTTPException(status_code=403, detail="Could not validate credentials")

# Global state container (avoiding module-level globals for clients)
class AppState:
    db_client: SurrealDBClient = None
    repository: SurrealDBMemoryRepository = None
    tools: KHALASubagentTools = None

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application."""
    # Startup
    logger.info("Initializing KHALA API...")
    try:
        # Load config safely
        config = SurrealConfig.from_env()
        state.db_client = SurrealDBClient(config)
        await state.db_client.initialize()

        state.repository = SurrealDBMemoryRepository(state.db_client)
        state.tools = KHALASubagentTools(repository=state.repository)
        logger.info("KHALA API initialized successfully.")
        yield
    except Exception as e:
        logger.critical(f"Startup failed: {e}")
        raise e
    finally:
        # Shutdown
        if state.db_client:
            await state.db_client.close()
        logger.info("KHALA API shutdown complete.")

app = FastAPI(title="Khala Memory API", version="2.1.0", lifespan=lifespan)

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """System health check."""
    if not state.db_client:
        raise HTTPException(status_code=503, detail="Database not initialized")

    try:
        # Check DB connection
        async with state.db_client.get_connection() as conn:
            await conn.query("RETURN true;")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")

@app.get("/metrics", dependencies=[Depends(get_api_key)])
async def get_metrics() -> Dict[str, Any]:
    """Retrieve system metrics (Authenticated)."""
    if not state.tools:
        raise HTTPException(status_code=503, detail="Tools not initialized")

    try:
        status = await state.tools.get_system_status()
        return status
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit", dependencies=[Depends(get_api_key)])
async def get_audit_logs() -> Dict[str, Any]:
    """Retrieve audit logs (Authenticated)."""
    # Placeholder for audit logging system
    return {"status": "not_implemented", "logs": []}
