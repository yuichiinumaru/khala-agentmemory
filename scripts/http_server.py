
import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import os
import asyncio

# Ensure correct path resolution
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

try:
    from khala.infrastructure.surrealdb.client import SurrealDBClient
    from khala.domain.memory.entities import Memory, MemoryTier, ImportanceScore
except ImportError as e:
    print(f"Failed to import Khala modules: {e}")
    # Fallback/Mock for build time checks if modules really missing
    SurrealDBClient = None

app = FastAPI(title="Khala Memory API")

# Initialize Client
SURREAL_URL = os.getenv("SURREALDB_URL", "ws://surrealdb:8000/rpc")
client = SurrealDBClient(url=SURREAL_URL) if SurrealDBClient else None

class CreateMemoryRequest(BaseModel):
    content: str
    user_id: str
    tags: List[str] = []
    category: Optional[str] = "generic"

@app.on_event("startup")
async def startup_event():
    if client:
        await client.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    if client:
        await client.close()

@app.get("/health")
async def health_check():
    return {"status": "ok", "surreal_url": SURREAL_URL, "modules_loaded": bool(client)}

@app.post("/memories")
async def create_memory(request: CreateMemoryRequest):
    if not client:
        raise HTTPException(status_code=503, detail="Khala Core not loaded")
    try:
        # Create entity (simplified for API)
        import uuid
        from datetime import datetime, timezone

        mem_id = f"memory:{uuid.uuid4()}"
        memory = Memory(
            id=mem_id,
            user_id=request.user_id,
            content=request.content,
            tier=MemoryTier.WORKING,
            importance=ImportanceScore.MEDIUM,
            tags=request.tags,
            category=request.category,
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
            accessed_at=datetime.now(timezone.utc)
        )

        saved_id = await client.create_memory(memory)
        return {"id": saved_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/memories/graph")
async def get_graph(limit: int = 100):
    if not client:
        return {"nodes": [], "edges": []}

    try:
        async with client.get_connection() as conn:
            # Safer query handling
            resp = await conn.query(f"SELECT * FROM memory ORDER BY created_at DESC LIMIT {limit}")

            raw_memories = []
            if isinstance(resp, list):
                 if len(resp) > 0 and 'result' in resp[0]:
                     raw_memories = resp[0]['result']
                 elif len(resp) > 0 and not 'result' in resp[0]:
                     # Maybe it's just the list
                     raw_memories = resp
            elif isinstance(resp, dict) and 'result' in resp:
                 raw_memories = resp['result']

            nodes = []
            edges = []

            for m in raw_memories:
                m_id = m.get('id', 'unknown')
                label = m.get('category', 'Memory')
                content = m.get('content', '')
                if content:
                    label = (content[:20] + '...') if len(content) > 20 else content

                nodes.append({
                    "id": m_id,
                    "label": label,
                    "type": m.get('tier', 'concept'),
                    "properties": {
                        "content": content,
                        "dateAdded": m.get('created_at')
                    }
                })

        return {"nodes": nodes, "edges": edges}

    except Exception as e:
        print(f"Graph Error: {e}")
        return {"nodes": [], "edges": []}

@app.get("/memories/search")
async def search_memories(q: str):
    if not client:
        return []

    try:
        # Using BM25 search from client
        # We need a user_id, let's assume default for now or pass in query
        results = await client.search_memories_by_bm25(q, user_id="user_default", top_k=5)

        # Serialize specific fields
        output = []
        for r in results:
             output.append(f"[Score: {r.get('score', 0)}] {r.get('content', '')}")

        return output
    except Exception as e:
        print(f"Search Error: {e}")
        return []

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
