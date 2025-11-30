# 03-ARCHITECTURE-TECHNICAL.md: Technical Architecture

**Project**: KHALA v2.0
**Reference**: [01-plan-overview.md](01-plan-overview.md)

---

## 1. System Overview

KHALA is designed as a **hierarchical, graph-based memory system** that integrates seamlessly with Agno agents. It leverages SurrealDB's multi-model capabilities to provide vector search, graph traversal, and document storage in a single unified layer.

### High-Level Components

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

## 2. Technology Stack Details

### Core Components
*   **Agno Framework**: The agent runtime environment. Handles prompt engineering, tool calling, and response generation.
*   **SurrealDB**: The "Brain". Stores vectors, knowledge graphs, and memory documents. Handles real-time subscriptions.
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

## 3. Module Architecture

### M01: Foundation (SurrealDB)
*   **Schema**: Rigid schema for core tables (`memory`, `entity`), flexible schema for metadata.
*   **RBAC**: Row-level security based on `user_id` and `namespace`.

### M02: Search System
*   **Hybrid Algorithm**:
    1.  **Candidate Generation**: Parallel execution of HNSW (Vector) and BM25 (Keyword).
    2.  **Filtering**: Apply metadata filters (time, tags).
    3.  **Reranking**: Reciprocal Rank Fusion (RRF) or LLM-based reranking.
    4.  **Context Assembly**: Fit results into token window.

### M03: Memory Lifecycle
*   **The 3 Tiers**:
    1.  **Working Memory**: Ephemeral, high-access. Stored in Redis/SurrealDB with short TTL.
    2.  **Short-Term Memory**: Consolidated daily. Stored in SurrealDB.
    3.  **Long-Term Memory**: Highly compressed, graph-connected.
*   **Consolidation**: A background process that merges similar memories and promotes significant ones.

### M05: Integration (MCP & Multi-Agent)
*   **MCP Server**: Exposes memory tools to any MCP-compliant client (e.g., Claude Desktop, other agents).
*   **LIVE Subscriptions**: Agents subscribe to table events.
    *   *Example*: Agent B listens for new 'task' memories created by Agent A.

---

## 4. Data Flow

### Write Flow (Storing Memory)
1.  **Input**: User message or Agent thought.
2.  **Extraction**: Extract entities, intent, and emotions.
3.  **Verification**: Check quality (is it worth saving?).
4.  **Embedding**: Generate vector.
5.  **Storage**: Write to `memory` table.
6.  **Graph Update**: Create/Update nodes in `entity` and edges in `relationship`.
7.  **Pub/Sub**: Notify listening agents via LIVE.

### Read Flow (Retrieving Context)
1.  **Query**: Agent asks a question.
2.  **Intent**: Classify intent (e.g., "Factual", "Reasoning").
3.  **Search**: Execute appropriate search strategy (Hybrid or Graph).
4.  **Ranking**: Sort by Relevance * Recency * Importance.
5.  **Assembly**: Format for LLM context window.

---

## 5. Security Architecture

*   **Authentication**: API Key / JWT.
*   **Authorization**: SurrealDB RBAC. Each user acts within their own `namespace`.
*   **Encryption**: TLS in transit, Disk encryption at rest.
*   **Audit**: Complete log of all memory modifications.

---

## 6. Scalability

*   **Horizontal**: SurrealDB clusters (future).
*   **Vertical**: Optimized Python code, async I/O.
*   **Cost**: Aggressive caching and LLM cascading to minimize API costs.
