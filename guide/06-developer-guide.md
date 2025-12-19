# The API: Developer Guide

How to extend Khala and integrate it into your agents.

## 1. Core Interface: `KHALAAgent`

This is your primary entry point.

```python
from khala.interface.agno.khala_agent import KHALAAgent

agent = KHALAAgent(...)

# Methods
await agent.memory.add(memory_input)         # Store
await agent.memory.search(query)             # Retrieve
await agent.memory.wipe()                    # Amnesia (Dev only)
await agent.audit.get_logs()                 # Inspection
```

## 2. Using the MCP Server

Khala exposes a Model Context Protocol (MCP) server for integration with other tools (like Claude Desktop or VIVI IDE).

**Resources Exposed:**
- `khala://memories/recent`: Get last 10 memories.
- `khala://entities/all`: List all known entities.

**Tools Exposed:**
- `store_memory(content, source)`
- `search_memory(query)`

## 3. Extending the Schema (Advanced)

To add new fields to the memory graph, you must edit the SurrealDB schema definitions in `khala/infrastructure/surrealdb/schema.py`.

**Steps:**
1. **Modify Schema**: Add your field to the `DEFINE TABLE memory SCHEMAFULL` section.
2. **Migration**: There is no auto-migration yet. You must execute the `DEFINE FIELD` command manually via the SurrealDB CLI or Khala Console.
3. **Update Entity**: Update the Pydantic model in `khala/domain/memory/entities.py`.

> [!WARNING]
> Changing the embedding model or vector dimension requires a full database wipe and re-indexing.

## 4. Creating a Custom Service

1. Create `khala/application/services/my_service.py`.
2. Inherit from the base `Service` class.
3. Inject `Repository` interfaces, not raw clients.
