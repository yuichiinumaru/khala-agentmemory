# 03-ARCHITECTURE.md
# KHALA v2.0: Complete Technical Architecture

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)  
**Version**: 2.0  
**Framework**: Agno + SurrealDB  
**Date**: November 2025

---

## 1. SYSTEM OVERVIEW

### 1.1 High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│ TIER 1: APPLICATION LAYER (Agno Agent)                     │
│                                                              │
│  - User interaction & orchestration                          │
│  - Tool invocation & planning                                │
│  - Multi-turn conversation management                        │
│  - Template agent interface                                  │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ TIER 2: INTELLIGENCE LAYER (Memory Processing)             │
│                                                              │
│  - Intent classification & routing                           │
│  - Multi-agent debate & consensus                            │
│  - Skill library extraction & management                     │
│  - Self-verification gates                                   │
│  - LLM cost cascading                                        │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ TIER 3: RETRIEVAL LAYER (Hybrid Search)                    │
│                                                              │
│  - Vector search (HNSW)                                      │
│  - BM25 full-text search                                     │
│  - Metadata filtering & tagging                              │
│  - Graph traversal (multi-hop)                               │
│  - Significance scoring & ranking                            │
│  - Dynamic context window assembly                           │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ TIER 4: STORAGE LAYER (SurrealDB)                          │
│                                                              │
│  - Vector storage (HNSW indexes)                             │
│  - Graph: entities + bi-temporal edges                       │
│  - Documents: flexible JSON model                            │
│  - Multimodal: images, tables, code                          │
│  - Audit trail: full decision history                        │
│  - Cache metadata: hit rates, TTLs                           │
└──────────────────────┬──────────────────────────────────────┘
                       ↓
┌─────────────────────────────────────────────────────────────┐
│ TIER 5: OPTIMIZATION LAYER (Background Processing)         │
│                                                              │
│  - Decay scoring (exponential)                               │
│  - Memory consolidation & merging                            │
│  - Deduplication (hash + semantic)                           │
│  - Pattern extraction → Skill library                        │
│  - Distributed processing (multi-worker)                     │
│  - GPU-accelerated embeddings                                │
└─────────────────────────────────────────────────────────────┘
```

### 1.2 Component Interaction Map

```
User Query
    ↓
┌─────────────────────────────────────────┐
│ Agno Agent (TIER 1)                     │
│ - Parse intent                          │
│ - Route to module                       │
│ - Call appropriate MCP tools            │
└─────────┬───────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│ Intelligence Layer (TIER 2)             │
│ - Intent Classification                 │
│ - Multi-Agent Debate                    │
│ - Verification Gate                     │
│ - LLM Cascade Router                    │
└─────────┬───────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│ Hybrid Search (TIER 3)                  │
│ - Vector search (HNSW)                  │
│ - BM25 search                           │
│ - Metadata filter                       │
│ - Graph traversal                       │
│ - Reranking & significance              │
└─────────┬───────────────────────────────┘
          ↓
┌─────────────────────────────────────────┐
│ SurrealDB (TIER 4)                      │
│ - Query execution                       │
│ - Index usage                           │
│ - Transaction handling                  │
│ - Multi-tenancy enforcement             │
└─────────┬───────────────────────────────┘
          ↓
Results returned to Agent → User
```

---

## 2. TECHNOLOGY STACK DETAILS

### 2.1 Primary Stack

**Agent Framework: Agno**
- GitHub: https://github.com/agno-agi/agno
- Version: Latest stable
- Integration: MCP server + WebSocket client
- Key Features:
  - Multi-turn conversations
  - Tool/function calling
  - Agent orchestration
  - Built-in memory interface

**Database: SurrealDB 2.0+**
- Website: https://surrealdb.com
- Version: 2.0 or higher
- Connection: WebSocket (ws://localhost:8000/rpc)
- Key Features:
  - Multimodel (document + graph + vector)
  - Native HNSW vector search
  - Graph relationships
  - LIVE real-time subscriptions
  - Built-in RBAC
  - Transactions support
  - Custom functions support

**LLM: Google Gemini**
- API: https://ai.google.dev
- Models:
  - `gemini-2.5-pro`: Complex reasoning ($0.1/1M tokens)
  - `gemini-1.5-flash`: Fast extraction ($0.0075/1M tokens)
  - `gemini-embedding-001`: Embeddings (768 dimensions)
- Integration: Google Generative AI Python SDK

**LLM: OpenAI (Fallback)**
- API: https://platform.openai.com
- Model: `gpt-4o-mini` for cascade medium tier ($0.015/1M tokens)
- Integration: OpenAI Python SDK

**Cache: Redis 7+**
- Website: https://redis.io
- Purpose: L2 cache layer
- Configuration:
  - TTL: 24 hours default
  - Namespaced keys
  - Connection pooling
- Key Features:
  - Fast in-memory storage
  - TTL support
  - Pub/Sub for coordination
  - Persistence (optional)

**Language: Python 3.11+**
- Version: 3.11 minimum
- Key Libraries:
  - `surrealdb-asyncio`: Async SurrealDB client
  - `google-generativeai`: Gemini API
  - `openai`: OpenAI API
  - `redis`: Redis client
  - `numpy`: Vector operations
  - `pydantic`: Data validation
  - `pytest`: Testing framework

### 2.2 Optional Infrastructure

**GPU Acceleration**
- NVIDIA CUDA 12+
- ONNX Runtime with GPU support
- cuBLAS for matrix operations
- Models:
  - ONNX-converted embeddings
  - GPU-accelerated search
  - 5x speedup target

**Monitoring & Observability**
- Prometheus: Metrics collection
- Grafana: Dashboard visualization
- ELK Stack: Log aggregation
- Jaeger: Distributed tracing (optional)

**Deployment**
- Docker: Containerization
- Kubernetes: Orchestration (optional)
- GitHub Actions: CI/CD

---

## 3. MODULE ARCHITECTURE

### 3.1 Module 01: Foundation

**Components**:
- `infrastructure/surrealdb/client.py` - Async SurrealDB wrapper
- `infrastructure/surrealdb/schema.surql` - Database schema
- `infrastructure/surrealdb/migrations/` - Schema migrations

**Key Classes**:
```
SurrealDBClient
├── connect()
├── query()
├── create()
├── update()
├── delete()
├── transaction()
└── close()

SurrealDBSchema
├── create_namespaces()
├── create_tables()
├── create_indexes()
└── create_functions()
```

**Data Models**:
```
Memory
├── id: string
├── user_id: string
├── content: string
├── embedding: vector[768]
├── tier: enum(working|short_term|long_term)
├── importance: float
├── tags: array<string>
├── metadata: object
└── created_at: datetime

Entity
├── id: string
├── text: string
├── type: string
├── embedding: vector[768]
├── confidence: float
└── metadata: object

Relationship (Graph Edge)
├── FROM: entity
├── TO: entity
├── relation_type: string
├── strength: float
├── valid_from: datetime
└── valid_to: datetime
```

**Dependencies**: None (foundation for all)

---

### 3.2 Module 02: Search System

**Components**:
- `domain/search/vector_search.py` - HNSW search
- `domain/search/bm25_search.py` - Full-text search
- `domain/search/metadata_filter.py` - Filtering
- `domain/search/hybrid_search.py` - Orchestrator
- `application/services/intent_classifier.py` - Intent routing
- `infrastructure/cache/cache_manager.py` - L1/L2/L3 caching
- `domain/search/context_assembler.py` - Context assembly
- `domain/search/significance_scorer.py` - Scoring

**Class Architecture**:
```
HybridSearcher
├── search(query, intent)
│   ├── Stage 1: Vector search (ANN)
│   ├── Stage 2: BM25 filtering
│   ├── Stage 3: Metadata filtering
│   ├── Stage 4: Graph traversal
│   └── Stage 5: Reranking
├── intent_classify(query) → Intent
└── score_significance(result) → float

IntentClassifier
├── classify(query) → Intent
├── pattern_search(query)
├── decision_search(query)
├── analysis_search(query)
└── standard_search(query)

CacheManager
├── L1_cache: LRU in-memory
├── L2_cache: Redis (24h TTL)
├── L3_cache: SurrealDB
└── hit_rate_tracking
```

**Search Pipeline**:
```
Query
  ↓
Intent Classification
  ├─ Factual (exact search)
  ├─ Pattern (graph traversal)
  ├─ Decision (importance filter)
  ├─ Analysis (hybrid + deep)
  └─ Other (standard)
  ↓
Vector Embedding (cache check)
  ├─ L1 hit? → Return immediately
  ├─ L2 hit? → Load to L1
  └─ L3/Generate (via Gemini)
  ↓
Vector Search (HNSW, top 100)
  ↓
BM25 Filtering (top 50)
  ↓
Metadata Filtering (by tags, category)
  ↓
Graph Traversal (if needed)
  ↓
Significance Scoring & Reranking
  ↓
Top-10 Results
```

**Dependencies**: Module 01

---

### 3.3 Module 03: Memory Lifecycle

**Components**:
- `domain/memory/tier_manager.py` - Tier management
- `domain/memory/memory_manager.py` - CRUD operations
- `domain/consolidation/consolidation_manager.py` - Consolidation
- `domain/consolidation/deduplicator.py` - Deduplication
- `domain/consolidation/merger.py` - Memory merging

**Tier Flow**:
```
New Memory
  ↓
Verification Gate (M07)
  ↓
Working Tier (1h TTL)
  ↓
  If: age > 0.5h AND access_count > 5 AND importance > 0.8
  → Promote to Short-Term
  ↓
Short-Term Tier (15d TTL)
  ↓
  If: age > 15d OR importance > 0.9
  → Promote to Long-Term
  ↓
Long-Term Tier (persistent)
  ↓
  If: age > 90d AND access_count = 0 AND importance < 0.3
  → Archive
```

**Consolidation Triggers**:
- Nightly (3 AM): Light consolidation
- Weekly (Sunday 2 AM): Deep consolidation
- Monthly (1st, 1 AM): Full optimization

**Consolidation Steps**:
```
1. Apply Decay Scoring
   score = importance × exp(-age_days / 30)

2. Identify Duplicates
   - Hash-based (exact): O(1)
   - Semantic (>0.95 similarity): O(n²)

3. Merge Similar Memories
   - Use LLM to generate merged version
   - Archive originals
   - Update relationships

4. Archive Old Memories
   - Criteria: age>90d, access=0, importance<0.3

5. Reindex & Optimize
   - Rebuild HNSW index
   - Compute statistics
```

**Dependencies**: Modules 01, 02

---

### 3.4 Module 04: Processing & Analysis

**Components**:
- `infrastructure/jobs/scheduler.py` - Job scheduling
- `domain/memory/entity_extractor.py` - NER
- `domain/memory/temporal_analyzer.py` - Temporal analysis
- `domain/memory/metadata_manager.py` - Tags system
- `domain/memory/memory_triggers.py` - Trigger detection
- `domain/memory/skill_library.py` - Skill extraction
- `domain/memory/instruction_registry.py` - Prompt library

**Entity Extraction Flow**:
```
Memory Content
  ↓
Gemini NER (fast model)
  ↓
Extract entities:
  - Person
  - Tool
  - Concept
  - Place
  - Event
  ↓
Assign confidence (0-1)
  ↓
Generate embeddings
  ↓
Store in entity table
  ↓
Auto-deduplicate
  ↓
Suggest relationships
  ↓
Create graph edges
```

**Memory Trigger Detection**:
```
Keyword Triggers:
  - "remember"
  - "important"
  - "don't forget"
  
Topic Change Detection:
  - Semantic distance > threshold
  - Cluster shift detected
  
Entity Novelty:
  - New entity detected
  - Rare entity encountered
```

**Skill Library Structure**:
```
Skill
├── id: string
├── name: string
├── description: string
├── preconditions: array<string>
├── steps: array<object>
├── postconditions: array<string>
├── success_rate: float
├── usage_count: int
├── confidence: float
└── tags: array<string>
```

**Dependencies**: Modules 01, 02, 03

---

### 3.5 Module 05: Integration & Coordination

**Components**:
- `interface/mcp/server.py` - MCP server
- `application/orchestration/agent_orchestrator.py` - Coordination
- `application/orchestration/multi_agent.py` - Multi-agent logic
- `infrastructure/monitoring/health_checker.py` - Health checks
- `infrastructure/monitoring/metrics_collector.py` - Metrics

**MCP Server Architecture**:
```
MCP Server (Port 3000)
  ├── Tool: store_memory
  │   └── Async wrapper around memory_manager.store()
  │
  ├── Tool: retrieve_memory
  │   └── Async wrapper around hybrid_search.search()
  │
  ├── Tool: search_graph
  │   └── Graph traversal queries
  │
  ├── Tool: consolidate
  │   └── Trigger consolidation job
  │
  └── Tool: get_context
      └── Context assembly
```

**Agent Orchestration**:
```
Multiple Agents Share:
  ├── Central Memory Store (SurrealDB)
  ├── Shared Knowledge Graph
  ├── LIVE subscriptions for real-time sync
  └── Debate mechanism for consensus

Event Flow:
  Agent A: stores memory
    ↓
  SurrealDB: records event
    ↓
  LIVE subscription notifies Agent B, C, D
    ↓
  Agents can access same memory
    ↓
  For critical decisions: trigger debate
```

**Health Check Metrics**:
```
DatabaseHealth
├── Connection: PING response time
├── Tables: Count of tables
├── Indexes: Index usage stats
└── Replication: Lag monitoring

CacheHealth
├── L1: Hit rate, size
├── L2: Hit rate, TTL health
└── L3: Query performance

ApplicationHealth
├── Agent uptime
├── Error rate
├── Latency (p50, p95, p99)
└── Memory usage
```

**Dependencies**: Modules 01, 02, 03, 04

---

### 3.6-3.10: Remaining Modules

[Due to space constraints, the remaining modules (06-10) follow the same architectural pattern as documented in 02-tasks.md]

**Module 06**: Cost Optimization
- LLMCascade router
- Consistency signal tracking
- Mixture of thought orchestrator

**Module 07**: Quality Assurance
- MemoryVerification (6 checks)
- MemoryDebate (3 agent consensus)
- Traceability logger

**Module 08**: Advanced Search
- Advanced indexing strategy
- Multi-perspective query expansion
- Topic change detector
- Cross-session pattern finder

**Module 09**: Production Features
- AuditLogger (complete trail)
- Distributed consolidation
- GPU accelerator
- Graph visualization API

**Module 10**: Advanced Capabilities
- Multimodal encoder
- Cross-modal retriever
- AST parser for code
- Dashboard backends

---

## 4. DATA FLOW DIAGRAMS

### 4.1 Memory Storage Flow

```
User Input
  ↓
Agno Agent
  ├─ Parse intent
  ├─ Validate input
  └─ Extract initial metadata
  ↓
LLM Cascade Router (M06)
  ├─ Complexity: high
  └─ Use gemini-2.5-pro
  ↓
Self-Verification Gate (M07)
  ├─ Check: Factual
  ├─ Check: Logic
  ├─ Check: Completeness
  ├─ Check: Embedding validity
  ├─ Check: Tags appropriateness
  └─ Check: Length validity
  ↓
  If score < 0.7 → Flag for review
  If score >= 0.7 → Continue
  ↓
Entity Extraction (M04)
  ├─ Extract entities (Gemini NER)
  ├─ Generate embeddings
  ├─ Deduplicate
  └─ Create relationships
  ↓
Multi-Agent Debate (M07)
  ├─ Analyzer: verify facts
  ├─ Synthesizer: check consistency
  ├─ Curator: evaluate importance
  └─ Consensus scoring
  ↓
Tier Assignment (M03)
  ├─ If importance > 0.8 → long_term
  ├─ If access_count likely → short_term
  └─ Else → working (default)
  ↓
Generate Main Embedding (M02, cached)
  ├─ L1 check: In-memory?
  ├─ L2 check: Redis?
  ├─ L3 check: SurrealDB?
  └─ Generate via Gemini-embedding-001
  ↓
Store to SurrealDB (M01)
  ├─ memory table
  ├── Vector index update
  └─ Trigger LIVE subscription
  ↓
Skill Extraction (M04, async)
  ├─ Pattern recognized?
  ├─ Extract as skill
  └─ Add to skill library
  ↓
Success Response
```

### 4.2 Search & Retrieval Flow

```
User Query
  ↓
Agno Agent
  └─ Call retrieve_memory tool
  ↓
Intent Classification (M02, M06 cascade)
  ├─ Simple query (fast model)
  │   └─ "What is X?"
  ├─ Pattern query (medium model)
  │   └─ "What patterns?"
  ├─ Decision query (smart model)
  │   └─ "What should we do?"
  └─ Complex query (smart model)
      └─ Deep analysis needed
  ↓
Cache Check (M02)
  ├─ Query embedding cache
  ├─ L1 hit? Return immediately
  ├─ L2 miss? Load to L1
  └─ L3 miss? Generate embedding
  ↓
Vector Search (HNSW, M02)
  ├─ Query embedding
  ├─ HNSW search: top 100 candidates
  ├─ Similarity threshold: >0.6
  └─ Return candidate set
  ↓
BM25 Full-Text (M02)
  ├─ Keyword search
  ├─ Relevance scoring
  └─ Filter to top 50
  ↓
Metadata Filtering (M02)
  ├─ User_id match
  ├─ Tag filtering
  ├─ Category filtering
  ├─ Date range filtering
  └─ Return top 20
  ↓
Graph Traversal (M02, if needed)
  ├─ Entity-based search
  ├─ Multi-hop relationships
  ├─ Temporal edges considered
  └─ Add relevant entities
  ↓
Significance Scoring (M08)
  ├─ Relevance: semantic similarity
  ├─ Repetition: occurrence frequency
  ├─ Recency: 1 - age_days/max_age
  ├─ Importance: memory importance score
  └─ Combined: weighted average
  ↓
Reranking & Deduplication (M02)
  ├─ Remove duplicates
  ├─ Sort by final score
  └─ Top 10 results
  ↓
Context Assembly (M02)
  ├─ Assemble results
  ├─ Token counting
  ├─ Dynamic window (model-specific)
  └─ Priority ranking
  ↓
Return to Agent
```

### 4.3 Consolidation Flow

```
Consolidation Trigger
  (Nightly 3AM / Weekly 2AM / Monthly 1AM)
  ↓
Load Batch of Memories
  (10k - 100k per batch)
  ↓
Apply Decay Scoring (M03, M06)
  ├─ decay = importance × exp(-age_days / 30)
  ├─ Update relevance_score
  └─ Mark for future archival
  ↓
Hash-Based Deduplication (M03)
  ├─ SHA256 content hash
  ├─ O(1) lookup for exact matches
  ├─ Merge exact duplicates
  └─ Archive originals
  ↓
Semantic Deduplication (M03)
  ├─ Cosine similarity > 0.95
  ├─ Candidate pairs identified
  ├─ LLM fusion
  │   └─ Generate merged version
  ├─ Store merged
  └─ Archive originals
  ↓
Pattern Extraction (M04)
  ├─ Identify recurring patterns
  ├─ Extract as skills
  ├─ Calculate success rates
  └─ Add to skill library
  ↓
Archive Old Memories (M03)
  ├─ Criteria:
  │   ├─ age > 90 days
  │   ├─ access_count = 0
  │   └─ importance < 0.3
  ├─ Mark as archived
  └─ Keep in cold storage
  ↓
Reindex (if distributed, M09)
  ├─ Worker 1: memories 0-25k
  ├─ Worker 2: memories 25k-50k
  ├─ Worker 3: memories 50k-75k
  ├─ Worker 4: memories 75k-100k
  ├─ Rebuild HNSW indexes
  └─ Merge results
  ↓
Compute Statistics
  ├─ Memory count per tier
  ├─ Average importance
  ├─ Growth rate
  └─ Storage usage
  ↓
Complete & Log
  ├─ Record completion time
  ├─ Audit trail
  └─ Update metrics
```

---

## 5. COMPONENT INTERACTIONS

### 5.1 Inter-Module Communication

**Module 01 ↔ All**
- Foundation: All modules depend on it
- SurrealDB client provided
- Schema contracts defined
- Query builders available

**Module 02 ↔ Module 03**
- Search ranks memories
- Consolidation updates relevance
- Tier affects search parameters

**Module 04 ↔ Module 03**
- Entities relate to memories
- Skills extracted during consolidation
- Tags enhance memory categorization

**Module 05 ↔ All**
- Orchestrator coordinates all modules
- LIVE subscriptions notify changes
- MCP tools expose all functions
- Health checks monitor all

**Module 06 ↔ Module 01, 02, 04**
- LLM routing applied to all LLM calls
- Cascade router in entity extraction
- Cascade router in search (intent classification)
- Cascade router in consolidation (merging)

**Module 07 ↔ Module 01, 03**
- Verification gate before storage
- Debate during consolidation
- Traceability for all decisions

---

## 6. API SPECIFICATIONS (Summary)

### 6.1 Internal Python APIs

**Memory Manager API**:
```python
class MemoryManager:
    async def store(content, tags, importance, tier) -> str
    async def retrieve(query, top_k, min_relevance) -> List[Memory]
    async def get_tier(tier, limit) -> List[Memory]
    async def promote(memory_id, target_tier) -> None
    async def delete(memory_id) -> None
```

**Hybrid Search API**:
```python
class HybridSearcher:
    async def search(query, intent, top_k) -> List[Result]
    async def vector_search(embedding, top_k) -> List[Result]
    async def graph_search(entity, depth) -> List[Result]
```

**Entity Manager API**:
```python
class EntityExtractor:
    async def extract(content) -> List[Entity]
    
class EntityManager:
    async def store(entity) -> str
    async def relate(entity1_id, relation_type, entity2_id) -> str
    async def get_relationships(entity_id, depth) -> List[Relationship]
```

### 6.2 External Interfaces

**MCP Tools**:
- `store_memory(content, tags, importance)`
- `retrieve_memory(query, top_k, min_relevance)`
- `search_graph(entity, depth, relation_types)`
- `consolidate()`
- `get_context(query, max_tokens)`

**REST API** (optional):
- `POST /memory` - Store memory
- `GET /memory/search` - Search
- `GET /memory/{id}` - Get memory
- `PUT /memory/{id}` - Update memory
- `DELETE /memory/{id}` - Delete memory
- `GET /health` - Health check
- `GET /metrics` - Prometheus metrics

**WebSocket API**:
- LIVE subscriptions to memory table
- Real-time event propagation
- Multi-agent coordination

---

## 7. SECURITY ARCHITECTURE

### 7.1 Authentication & Authorization

**Multi-Tenancy Model**:
```
User A (Namespace: user_a)
  ├─ Database: memory_db
  ├─ Tables: user_a.memory, user_a.entity
  └─ RBAC: Only user_a can access

User B (Namespace: user_b)
  ├─ Database: memory_db
  ├─ Tables: user_b.memory, user_b.entity
  └─ RBAC: Only user_b can access
```

**Role-Based Access Control**:
```
Roles:
  - Owner: Full control (read, write, delete)
  - Contributor: Write + read
  - Viewer: Read only
  - System: Internal processes
```

**API Security**:
```
Authentication Methods:
  - API Key (header: X-API-Key)
  - JWT Token (bearer token)
  - Service-to-service mTLS (optional)

Authorization:
  - Per-endpoint permissions
  - Row-level security (user_id filtering)
  - Resource ownership validation
```

### 7.2 Data Protection

**Encryption**:
- At-rest: AES-256 in database (SurrealDB native)
- In-transit: TLS 1.3 (WebSocket over wss://)
- API: HTTPS only

**Key Management**:
- API keys rotated every 90 days
- Secrets stored in secure vault
- No hardcoded credentials

**Audit Trail**:
- Every action logged to audit_log table
- Immutable logs
- Retention: 1 year minimum
- Query: User, timestamp, action, before/after

---

## 8. PERFORMANCE ARCHITECTURE

### 8.1 Caching Strategy

**L1 Cache (In-Memory LRU)**:
```
Purpose: Ultra-fast access
Size: 1000 embeddings
TTL: Session lifetime
Hit rate target: >70%
```

**L2 Cache (Redis)**:
```
Purpose: Cross-request caching
TTL: 24 hours
Keys: emb:{sha256(text)}
Hit rate target: >80%
```

**L3 Cache (SurrealDB)**:
```
Purpose: Persistent storage
Tables: memory, entity
Indexes: HNSW, BM25
```

### 8.2 Indexing Strategy

**HNSW Vector Index**:
```
Table: memory
Field: embedding (768 dimensions)
Parameters:
  - M: 16 (connections per node)
  - ef_construction: 200 (construction accuracy)
  - ef_runtime: 50 (query accuracy)
Latency: p95 < 100ms for 1M vectors
```

**BM25 Full-Text Index**:
```
Table: memory
Field: content
Index type: FULLTEXT
Query: content @@ "keyword search"
Precision: >85%
```

**B-Tree Indexes**:
```
- memory.user_id (for user segmentation)
- memory.tier (for tier filtering)
- memory.created_at (for time-based queries)
- entity.type (for entity type filtering)
```

**Composite Indexes** (Hot Path):
```
- (user_id, importance DESC, created_at DESC)
- (user_id, tier, accessed_at DESC)
```

### 8.3 Query Optimization

**Index Selection**:
- Query planner automatically uses best index
- EXPLAIN PLAN analysis for complex queries
- Manual hints if needed

**Query Rewriting**:
- Combine conditions to use composite indexes
- Predicate pushdown to database
- Avoid N+1 queries

---

## 9. SCALABILITY DESIGN

### 9.1 Horizontal Scaling

**Distributed Consolidation** (M09):
```
Single Consolidation Job
  ├─ Worker 1: Memories 0-25%
  ├─ Worker 2: Memories 25-50%
  ├─ Worker 3: Memories 50-75%
  └─ Worker 4: Memories 75-100%
  ↓
Parallel Processing
  └─ 4-5x speedup expected

Merge Results
  └─ Single consolidation takes 5 min instead of 20-25
```

**Database Sharding** (Future):
```
User A-G: Shard 1
User H-O: Shard 2
User P-W: Shard 3
User X-Z: Shard 4
```

### 9.2 Vertical Scaling

**GPU Acceleration** (M09):
```
CPU Baseline:
  - Embedding generation: ~100/second
  
GPU Accelerated:
  - ONNX Runtime GPU: ~500-1000/second
  - 5-10x speedup
```

**Multi-Node Deployment**:
```
Node 1: SurrealDB Primary
Node 2: SurrealDB Replica
Node 3: Redis Master
Node 4: Redis Replica
Node 5-6: Application servers
```

---

## 10. REFERENCES

### Official Documentation
- Agno: https://docs.agno.com
- SurrealDB: https://surrealdb.com/docs
- Gemini API: https://ai.google.dev/docs
- Redis: https://redis.io/docs

### Architecture Patterns
- CQRS: https://martinfowler.com/bliki/CQRS.html
- Event Sourcing: https://martinfowler.com/eaaDev/EventSourcing.html
- Multi-Agent: https://arxiv.org/abs/2309.07864
- Vector Search: https://arxiv.org/abs/2310.08560

---

**END OF 03-ARCHITECTURE.MD**

See 04-database.md for database schema details.
