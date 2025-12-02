from fastapi import FastAPI, HTTPException
import logging
from typing import Dict, Any

from ...infrastructure.surrealdb.client import SurrealDBClient
from ...infrastructure.persistence.surrealdb_repository import SurrealDBMemoryRepository
from ...interface.mcp.khala_subagent_tools import KHALASubagentTools
import os

app = FastAPI(title="Khala Memory API", version="2.0.0")
logger = logging.getLogger(__name__)

# Initialize dependencies (global for now, could be dependency injected)
SURREAL_URL = os.getenv("SURREAL_URL", "ws://localhost:8000/rpc")
SURREAL_USER = os.getenv("SURREAL_USER", "root")
SURREAL_PASS = os.getenv("SURREAL_PASS", "root")
SURREAL_NS = os.getenv("SURREAL_NS", "khala")
SURREAL_DB = os.getenv("SURREAL_DB", "memories")

db_client = SurrealDBClient(
    url=SURREAL_URL,
    username=SURREAL_USER,
    password=SURREAL_PASS,
    namespace=SURREAL_NS,
    database=SURREAL_DB
)
repository = SurrealDBMemoryRepository(db_client)
khala_tools = KHALASubagentTools(repository=repository)


@app.get("/health")
async def health_check() -> Dict[str, str]:
    """System health check."""
    try:
        # Check DB connection
        async with db_client.get_connection() as conn:
            await conn.query("RETURN true;")
        return {"status": "ok", "database": "connected"}
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail=f"Service unavailable: {e}")

@app.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Retrieve system metrics."""
    try:
        status = await khala_tools.get_system_status()
        return status
    except Exception as e:
        logger.error(f"Metrics collection failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/audit")
async def get_audit_logs() -> Dict[str, Any]:
    """Retrieve audit logs."""
    # Placeholder for audit logging system
    return {"status": "not_implemented", "logs": []}

@app.post("/admin/reset")
async def reset_memory() -> Dict[str, str]:
    """Wipes memory (Admin only)."""
    # Implementation pending security/auth layer
    raise HTTPException(status_code=501, detail="Not implemented")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
