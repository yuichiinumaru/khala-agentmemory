# 05-API.md
# KHALA v2.0: API Specifications

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)  
**Version**: 2.0  
**Date**: November 2025

---

## 1. MCP TOOLS (Primary Interface)

### 1.1 store_memory()

**Purpose**: Store new memory with all validations  
**Priority**: P0 (core)

```python
{
  "name": "store_memory",
  "description": "Store a new memory with automatic validation, embedding, and tier assignment",
  "inputSchema": {
    "type": "object",
    "properties": {
      "content": {
        "type": "string",
        "description": "Memory content (5-50000 chars)"
      },
      "tags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Memory tags for categorization"
      },
      "importance": {
        "type": "number",
        "minimum": 0,
        "maximum": 1,
        "description": "Importance score (0-1)"
      },
      "category": {
        "type": "string",
        "description": "Memory category (optional)"
      }
    },
    "required": ["content"]
  },
  "output": {
    "memory_id": "string (UUID)",
    "tier": "string (working|short_term|long_term)",
    "stored_at": "datetime",
    "verification_score": "float (0-1)"
  }
}
```

**Flow**:
1. Validate input (length, format)
2. Run verification gate (6 checks)
3. Generate embedding (cached)
4. Multi-agent debate
5. Assign tier based on importance
6. Store to SurrealDB
7. Return memory_id

**Errors**:
- 400: Invalid input
- 402: LLM cost limit exceeded
- 500: Storage error

---

### 1.2 retrieve_memory()

**Purpose**: Search for relevant memories  
**Priority**: P0 (core)

```python
{
  "name": "retrieve_memory",
  "description": "Search for memories using hybrid search (vector + BM25 + metadata)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Search query"
      },
      "top_k": {
        "type": "integer",
        "default": 10,
        "minimum": 1,
        "maximum": 50
      },
      "min_relevance": {
        "type": "number",
        "default": 0.5,
        "minimum": 0,
        "maximum": 1
      },
      "tags": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Filter by tags"
      },
      "tier": {
        "type": "string",
        "enum": ["working", "short_term", "long_term"],
        "description": "Filter by tier"
      }
    },
    "required": ["query"]
  },
  "output": {
    "results": [
      {
        "memory_id": "string",
        "content": "string",
        "relevance": "float (0-1)",
        "significance": "float (0-1)",
        "tags": ["string"],
        "created_at": "datetime"
      }
    ],
    "search_latency_ms": "number",
    "cache_hit": "boolean"
  }
}
```

**Pipeline**:
1. Intent classification (route to specialized search)
2. Vector embedding (cached)
3. Vector search (top 100)
4. BM25 filtering
5. Metadata filtering
6. Graph traversal (if needed)
7. Significance scoring
8. Reranking & dedup
9. Return top-k

---

### 1.3 search_graph()

**Purpose**: Traverse knowledge graph  
**Priority**: P1

```python
{
  "name": "search_graph",
  "description": "Traverse entity relationship graph",
  "inputSchema": {
    "type": "object",
    "properties": {
      "entity_id": {"type": "string"},
      "depth": {
        "type": "integer",
        "default": 1,
        "minimum": 1,
        "maximum": 3
      },
      "relation_types": {
        "type": "array",
        "items": {"type": "string"},
        "description": "Filter by relation types"
      }
    },
    "required": ["entity_id"]
  },
  "output": {
    "entities": [{"id": "string", "text": "string", "type": "string"}],
    "relationships": [
      {
        "source": "string",
        "target": "string",
        "type": "string",
        "strength": "float"
      }
    ]
  }
}
```

---

### 1.4 consolidate()

**Purpose**: Trigger consolidation  
**Priority**: P1

```python
{
  "name": "consolidate",
  "description": "Trigger memory consolidation (merge, deduplicate, archive)",
  "inputSchema": {
    "type": "object",
    "properties": {
      "mode": {
        "type": "string",
        "enum": ["light", "deep", "full"],
        "default": "light",
        "description": "Consolidation intensity"
      },
      "batch_size": {
        "type": "integer",
        "default": 10000,
        "minimum": 100,
        "maximum": 100000
      }
    }
  },
  "output": {
    "consolidated": "integer",
    "merged": "integer",
    "archived": "integer",
    "duration_seconds": "float"
  }
}
```

---

### 1.5 get_context()

**Purpose**: Assemble optimized context  
**Priority**: P1

```python
{
  "name": "get_context",
  "description": "Get assembled context window for LLM",
  "inputSchema": {
    "type": "object",
    "properties": {
      "query": {
        "type": "string",
        "description": "Context query"
      },
      "max_tokens": {
        "type": "integer",
        "default": 4000,
        "minimum": 1000,
        "maximum": 128000
      },
      "model": {
        "type": "string",
        "default": "gemini-3-pro-preview",
        "description": "Target model for token counting"
      }
    },
    "required": ["query"]
  },
  "output": {
    "context": "string (assembled context)",
    "memories_count": "integer",
    "token_count": "integer",
    "assembled_at": "datetime"
  }
}
```

---

## 2. REST API (Optional)

### 2.1 Core Endpoints

```
POST /api/v1/memory
  Store memory
  Body: {content, tags, importance}
  Return: {memory_id, created_at}

GET /api/v1/memory?query=search_term&top_k=10
  Search memories
  Return: {results: [...]}

GET /api/v1/memory/{id}
  Get specific memory
  Return: {memory: {...}}

PUT /api/v1/memory/{id}
  Update memory
  Body: {importance, tags}
  Return: {updated_at}

DELETE /api/v1/memory/{id}
  Delete memory
  Return: {deleted: true}

GET /api/v1/health
  Health check
  Return: {status: "healthy", db: "ok", cache: "ok"}

GET /api/v1/metrics
  Prometheus metrics
  Return: Prometheus format
```

### 2.2 Query Parameters

**Pagination**:
```
?offset=0&limit=10
?page=1&page_size=50
```

**Filtering**:
```
?tags=important,project
?tier=short_term
?min_importance=0.7
?created_after=2024-01-01
```

**Sorting**:
```
?sort_by=importance&order=desc
?sort_by=created_at&order=asc
```

---

## 3. AUTHENTICATION & AUTHORIZATION

### 3.1 API Key Auth

```
Header: X-API-Key: {api_key}
```

### 3.2 JWT Token Auth

```
Header: Authorization: Bearer {jwt_token}
```

### 3.3 RBAC Roles

```
- owner: Full access (read, write, delete, admin)
- editor: Read + write
- viewer: Read only
- system: Internal processes only
```

---

## 4. ERROR HANDLING

### 4.1 Error Response Format

```json
{
  "error": {
    "code": "INVALID_INPUT",
    "message": "Memory content too short (minimum 5 characters)",
    "details": {
      "field": "content",
      "value": "hi",
      "constraint": "min_length:5"
    },
    "timestamp": "2024-01-01T12:00:00Z"
  }
}
```

### 4.2 Error Codes

| Code | Status | Meaning |
|------|--------|---------|
| INVALID_INPUT | 400 | Input validation failed |
| UNAUTHORIZED | 401 | Missing/invalid auth |
| FORBIDDEN | 403 | Insufficient permissions |
| NOT_FOUND | 404 | Resource not found |
| CONFLICT | 409 | Resource conflict |
| RATE_LIMIT | 429 | Rate limit exceeded |
| LLM_ERROR | 502 | LLM API failed |
| DATABASE_ERROR | 500 | Database error |

---

## 5. RATE LIMITING

### 5.1 Limits

```
store_memory:  100/hour per API key
retrieve:      1000/hour per API key
search_graph:  500/hour per API key
consolidate:   5/day per API key
get_context:   500/hour per API key
```

### 5.2 Rate Limit Headers

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 45
X-RateLimit-Reset: 1234567890
```

---

## 6. VERSIONING

### 6.1 API Versions

```
v1: Current stable
v2: Development (optional)
```

### 6.2 Deprecation Policy

```
- 1: Feature marked as deprecated
- 6 months: Continue working with warnings
- 12 months: Final removal
```

---

## 7. REFERENCES

- MCP Protocol: https://modelcontextprotocol.io/
- REST API Design: https://restfulapi.net/
- JSON Schema: https://json-schema.org/

---

**END OF 05-API.MD**
