from fastapi import FastAPI, HTTPException, Depends, Security
from fastapi.security import APIKeyHeader
import logging
import secrets
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
    """Validate API Key using constant-time comparison."""
    expected_key = os.getenv("KHALA_API_KEY")
    if not expected_key:
        # Fail closed silently on request path to prevent log flooding
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    if not api_key_header or not secrets.compare_digest(api_key_header, expected_key):
        raise HTTPException(status_code=403, detail="Invalid credentials")

    return api_key_header

# Global state container
class AppState:
    db_client: SurrealDBClient = None
    repository: SurrealDBMemoryRepository = None
    tools: KHALASubagentTools = None

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application."""
    logger.info("Initializing KHALA API...")

    # Pre-flight check
    if not os.getenv("KHALA_API_KEY"):
        logger.critical("KHALA_API_KEY not set. API is insecure/broken.")
        # We don't raise here to allow app to start for fixing, but requests will fail 500.

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
        # Allow shutdown cleanup
        yield
    finally:
        if state.db_client:
            await state.db_client.close()
        logger.info("KHALA API shutdown complete.")

app = FastAPI(title="Khala Memory API", version="2.1.0", lifespan=lifespan)

@app.get("/health")
async def health_check() -> Dict[str, str]:
    """Liveness check (No DB query)."""
    return {"status": "ok"}

@app.get("/ready", dependencies=[Depends(get_api_key)])
async def readiness_check() -> Dict[str, str]:
    """Readiness check (DB Connectivity). Authenticated."""
    if not state.db_client:
        raise HTTPException(status_code=503, detail="Database not initialized")

    try:
        async with state.db_client.get_connection() as conn:
            await conn.query("RETURN true;")
        return {"status": "ready", "database": "connected"}
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unavailable")

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
        raise HTTPException(status_code=500, detail="Internal Error")

@app.get("/audit", dependencies=[Depends(get_api_key)])
async def get_audit_logs() -> Dict[str, Any]:
    """Retrieve audit logs (Authenticated)."""
    return {"status": "not_implemented", "logs": []}
