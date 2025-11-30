# 003-TECH-ARCHITECTURE.md: Technical Specifications

**Project**: KHALA v2.0
**Reference**: [001-project-plan-and-tasks.md](001-project-plan-and-tasks.md)

---

## 1. System Overview

KHALA is designed as a **hierarchical, graph-based memory system** that integrates seamlessly with Agno agents. It leverages SurrealDB's multi-model capabilities to provide vector search, graph traversal, and document storage in a single unified layer.

### High-Level Architecture

```mermaid
graph TD
    User[User / Agno Agent] -->|Interaction| API[Interface Layer (API/MCP)]
    API --> Orchestrator[Application Layer: Orchestrator]

    subgraph "Layer 1: Intelligence"
        Orchestrator --> Intent[Intent Classifier]
        Orchestrator --> Debate[Multi-Agent Debate]
        Orchestrator --> Verify[Verification Gate]
    end

    subgraph "Layer 2: Retrieval Engine"
        Intent --> Hybrid[Hybrid Search]
        Hybrid --> Vector[Vector Search]
        Hybrid --> BM25[BM25 Search]
        Hybrid --> GraphSearch[Graph Traversal]
        Hybrid --> Cache[L1/L2 Cache]
    end

    subgraph "Layer 3: Storage (SurrealDB)"
        Vector --> DB_Mem[(Memory Table)]
        BM25 --> DB_Mem
        GraphSearch --> DB_Graph[(Entity & Relation Tables)]
    end

    subgraph "Layer 4: Background Optimization"
        Scheduler[Job Scheduler] --> Consolidation[Consolidation Service]
        Scheduler --> Decay[Decay Service]
        Scheduler --> Skill[Skill Extractor]
        Consolidation --> DB_Mem
    end
```

---

## 2. Technology Stack

### Core Components
*   **Agno Framework**: The agent runtime environment. Handles prompt engineering, tool calling, and response generation.
*   **SurrealDB 2.0+**: The "Brain". Stores vectors, knowledge graphs, and memory documents. Handles real-time subscriptions.
    *   *Modes*: Multi-model (Document + Graph + Vector).
    *   *Configuration*: WebSocket mode for LIVE updates.
*   **LLM Tiering**:
    *   *Fast*: Gemini 1.5 Flash (Classification, simple extraction).
    *   *Medium*: GPT-4o-mini (Summarization, routine reasoning).
    *   *Smart*: Gemini 2.5 Pro (Complex deduction, debate, coding).

### Infrastructure
*   **Redis**: L2 Cache for frequent queries and session state.
*   **Python 3.11+**: Core logic implementation (Async/Await).
*   **Prometheus/Grafana**: Monitoring and observability.

---

## 3. Database Schema (SurrealDB)

### Namespaces & Databases
*   **Namespace**: `khala` (Production), `khala_dev` (Development).
*   **Database**: `memory_store`.

### Tables Definition

#### `memory` (Document + Vector)
Primary storage for agent memories.
```surrealql
DEFINE TABLE memory SCHEMAFULL
    PERMISSIONS FOR select, create, update, delete WHERE user_id = $auth.id;

DEFINE FIELD id ON memory TYPE record;
DEFINE FIELD user_id ON memory TYPE string;
DEFINE FIELD content ON memory TYPE string;
DEFINE FIELD embedding ON memory TYPE array<float>; -- 768 dimensions
DEFINE FIELD created_at ON memory TYPE datetime DEFAULT time::now();
DEFINE FIELD updated_at ON memory TYPE datetime DEFAULT time::now();
DEFINE FIELD tier ON memory TYPE string ASSERT $value IN ['working', 'short_term', 'long_term'];
DEFINE FIELD importance ON memory TYPE float ASSERT $value >= 0 AND $value <= 1;
DEFINE FIELD tags ON memory TYPE array<string>;
DEFINE FIELD summary ON memory TYPE string; -- Added in Module 11
DEFINE FIELD content_hash ON memory TYPE string; -- Added for Deduplication
DEFINE FIELD metadata ON memory TYPE object FLEXIBLE;

-- Indexes
DEFINE INDEX idx_memory_embedding ON memory FIELDS embedding MTPREE DIMENSION 768 DIST M=16 EF=200; -- HNSW
DEFINE INDEX idx_memory_content_ft ON memory FIELDS content FULLTEXT; -- BM25
DEFINE INDEX idx_memory_user_tier ON memory FIELDS user_id, tier;
DEFINE INDEX content_hash_index ON memory FIELDS content_hash; -- Deduplication
```

#### `entity` (Graph Node)
Represents extracted entities (People, Places, Concepts).
```surrealql
DEFINE TABLE entity SCHEMAFULL;

DEFINE FIELD name ON entity TYPE string;
DEFINE FIELD type ON entity TYPE string;
DEFINE FIELD description ON entity TYPE string;
DEFINE FIELD embedding ON entity TYPE array<float>;
DEFINE FIELD aliases ON entity TYPE array<string>;
DEFINE FIELD last_seen ON entity TYPE datetime;

DEFINE INDEX idx_entity_name ON entity FIELDS name UNIQUE;
DEFINE INDEX idx_entity_embedding ON entity FIELDS embedding MTPREE DIMENSION 768 DIST M=16;
```

#### `relationship` (Graph Edge)
Represents connections between entities.
```surrealql
DEFINE TABLE relationship SCHEMAFULL TYPE RELATION IN entity OUT entity;

DEFINE FIELD type ON relationship TYPE string; -- e.g., 'KNOWS', 'LOCATED_AT'
DEFINE FIELD weight ON relationship TYPE float;
DEFINE FIELD first_seen ON relationship TYPE datetime;
DEFINE FIELD last_verified ON relationship TYPE datetime;
DEFINE FIELD bi_temporal_start ON relationship TYPE datetime;
DEFINE FIELD bi_temporal_end ON relationship TYPE datetime;
```

#### `audit_log` (Compliance)
Logs all changes to memory.
```surrealql
DEFINE TABLE audit_log SCHEMAFULL;

DEFINE FIELD timestamp ON audit_log TYPE datetime DEFAULT time::now();
DEFINE FIELD actor ON audit_log TYPE string;
DEFINE FIELD action ON audit_log TYPE string; -- 'CREATE', 'MERGE', 'DELETE'
DEFINE FIELD target_id ON audit_log TYPE record;
DEFINE FIELD details ON audit_log TYPE object;
```

#### `skill` (Skill Library)
Executable skills learned by the agent.
```surrealql
DEFINE TABLE skill SCHEMAFULL;

DEFINE FIELD name ON skill TYPE string;
DEFINE FIELD code ON skill TYPE string;
DEFINE FIELD description ON skill TYPE string;
DEFINE FIELD usage_count ON skill TYPE int DEFAULT 0;
DEFINE FIELD success_rate ON skill TYPE float DEFAULT 0.0;
```

### Custom Functions

```surrealql
-- Decay Score: Calculates memory relevance based on time
DEFINE FUNCTION fn::decay_score($age_days: float, $half_life: float) {
    RETURN 1.0 / (1.0 + math::pow($age_days / $half_life, 2));
};

-- Similarity Threshold: Helper for vector search
DEFINE FUNCTION fn::is_similar($vec1: array, $vec2: array, $threshold: float) {
    RETURN vector::similarity::cosine($vec1, $vec2) >= $threshold;
};
```

---

## 4. API & Integration

### Internal Python API
Direct integration for Agno agents.
```python
from khala.interface.agno import KhalaMemory

memory = KhalaMemory()
# Storing
await memory.add("The user likes dark mode.", tags=["preference"])
# Retrieval
context = await memory.search("What does the user like?", limit=3)
```

### MCP Interface (Model Context Protocol)
Standardized tools for external agents (Claude Desktop, etc.).

*   **`store_memory`**: Stores new fragment. Args: `content`, `tags`, `importance`.
*   **`retrieve_memory`**: Semantic search. Args: `query`, `limit`, `threshold`.
*   **`search_graph`**: Graph traversal. Args: `entity_name`, `depth`, `relation_type`.
*   **`consolidate_now`**: Triggers manual consolidation.

### Multi-Agent Protocol
Agents coordinate using SurrealDB LIVE queries.
*   **Events**: `MEMORY_CREATED`, `DEBATE_REQUEST`, `CONSENSUS_REACHED`.
*   **Subscription**: `LIVE SELECT * FROM memory WHERE tier = 'long_term';`

### REST API (Management)
*   `GET /health`: System health check.
*   `GET /metrics`: Prometheus metrics.
*   `GET /audit`: Retrieve audit logs.
*   `POST /admin/reset`: Wipes memory (Admin only).

---

## 5. Security & Scalability

*   **Security**:
    *   Authentication via API Key / JWT.
    *   Authorization via SurrealDB RBAC (Namespace isolation).
    *   Encryption via TLS (transit) and disk encryption (rest).
*   **Scalability**:
    *   Horizontal scaling via SurrealDB clusters.
    *   Vertical optimization via async Python code.
    *   Cost control via aggressive caching and LLM cascading.
