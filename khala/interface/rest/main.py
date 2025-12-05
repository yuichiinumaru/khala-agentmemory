from fastapi import FastAPI, HTTPException, Depends, Security, Request
from fastapi.security import APIKeyHeader
import logging
import secrets
from typing import Dict, Any, AsyncGenerator, Optional
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

# Global state container
class AppState:
    db_client: Optional[SurrealDBClient] = None
    repository: Optional[SurrealDBMemoryRepository] = None
    tools: Optional[KHALASubagentTools] = None
    api_key: Optional[str] = None

state = AppState()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifecycle manager for the application."""
    logger.info("Initializing KHALA API...")

    # Load Secrets ONCE
    api_key = os.getenv("KHALA_API_KEY")
    if not api_key:
        logger.critical("KHALA_API_KEY not set. Refusing to start.")
        raise RuntimeError("KHALA_API_KEY environment variable is missing.")

    state.api_key = api_key

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
        # Fail Fast: Do not yield control if startup fails
        raise RuntimeError(f"Application Startup Failed: {e}") from e

    finally:
        if state.db_client:
            await state.db_client.close()
        logger.info("KHALA API shutdown complete.")

app = FastAPI(title="Khala Memory API", version="2.1.0", lifespan=lifespan)

def get_api_key(api_key_header: str = Security(api_key_header)):
    """Validate API Key using constant-time comparison.

    Uses state loaded at startup to avoid OS calls per request.
    """
    if not state.api_key:
        # Should be unreachable if lifespan works, but defensive coding
        raise HTTPException(status_code=500, detail="Server misconfiguration")

    if not api_key_header or not secrets.compare_digest(api_key_header, state.api_key):
        raise HTTPException(status_code=403, detail="Invalid credentials")

    return api_key_header

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
