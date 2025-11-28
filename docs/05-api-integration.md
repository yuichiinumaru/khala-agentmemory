# 05-API-INTEGRATION.md: API & Integration Specs

**Project**: KHALA v2.0
**Reference**: [03-architecture-technical.md](03-architecture-technical.md)

---

## 1. Overview

KHALA exposes its capabilities through three primary interfaces:
1.  **Internal Python API**: For direct integration into Agno agents.
2.  **MCP Server**: For external agents (Claude, etc.) via Model Context Protocol.
3.  **REST API**: For dashboards and monitoring.

---

## 2. MCP Interface (Model Context Protocol)

The MCP server allows any MCP-compliant client to "plug in" KHALA as a memory tool.

### Tools Exposed

#### `store_memory`
Stores a new memory fragment.
*   **Args**:
    *   `content` (string): The text to store.
    *   `tags` (list[string]): Optional tags.
    *   `importance` (float): 0.0 to 1.0.
*   **Returns**: Memory ID.

#### `retrieve_memory`
Semantically searches for memories.
*   **Args**:
    *   `query` (string): Search query.
    *   `limit` (int): Max results (default 5).
    *   `threshold` (float): Min similarity (default 0.7).
*   **Returns**: List of memory objects.

#### `search_graph`
Traverses the knowledge graph.
*   **Args**:
    *   `entity_name` (string): Starting node.
    *   `depth` (int): How many hops (default 1).
    *   `relation_type` (string): Filter by relation.
*   **Returns**: Graph subgraph (nodes + edges).

#### `consolidate_now`
Triggers manual consolidation.
*   **Args**: None.
*   **Returns**: Status report (items merged, deleted).

---

## 3. Internal Python API

Direct usage within Agno.

```python
from khala.interface.agno import KhalaMemory

memory = KhalaMemory()

# Storing
await memory.add("The user likes dark mode.", tags=["preference"])

# Retrieval
context = await memory.search("What does the user like?", limit=3)
```

---

## 4. Multi-Agent Protocol

Agents communicate and coordinate using SurrealDB LIVE queries.

### Event Types

*   `MEMORY_CREATED`: Emitted when new info is stored.
*   `DEBATE_REQUEST`: Emitted when an agent needs a second opinion.
*   `CONSENSUS_REACHED`: Emitted when debate concludes.

### Subscription Example (SurrealQL)

```surrealql
LIVE SELECT * FROM memory WHERE tier = 'long_term';
```

---

## 5. REST API (Management)

*   `GET /health`: System health check.
*   `GET /metrics`: Prometheus metrics.
*   `GET /audit`: Retrieve audit logs.
*   `POST /admin/reset`: Wipes memory (Admin only).

---

## 6. Error Handling

*   **4xx**: Client errors (Invalid params, Auth failure).
*   **5xx**: Server errors (DB down, LLM API fail).
*   **Retries**: Exponential backoff implemented for all LLM and DB calls.
