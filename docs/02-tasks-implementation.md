# 02-TASKS-IMPLEMENTATION.md: Complete Task Breakdown

**Project**: KHALA v2.0
**Reference**: [01-plan-overview.md](01-plan-overview.md)
**Status**: Active

---

## Review Findings (Modules 01-05)
*Review Conducted by Jules*

**Summary**: Modules 01-05 are largely implemented with high fidelity. However, critical integration gaps exist in the Foundation module, and some automation features are missing.

**Critical Gaps**:
1.  **Schema Discrepancy (M01)**: The active database client (`client.py`) uses a hardcoded, incomplete schema initialization that differs from the comprehensive `schema.py`. Consequently, **Custom Functions** (Decay/Promotion) and **RBAC Roles** are defined in code but never deployed to the database.
2.  **Deduplication (M03)**: No mechanism exists to prevent duplicate memory creation (Hash-based deduplication is missing).
3.  **Consolidation Automation (M03)**: While "Smart Consolidation" logic exists via Agents, there is no scheduled job to trigger it automatically.

---

## Task Organization
- **Format**: `M{module}.{category}.{task}`
- **Priorities**: P0 (Critical), P1 (High), P2 (Medium), P3 (Low)
- **Status**: TODO, IN_PROGRESS, REVIEW, DONE

---

## Module 01: Foundation (Core Infrastructure)

### Setup & Environment
- [x] **M01.SETUP.001** [P0]: Install Python 3.11+ & Dependencies.
- [x] **M01.SETUP.002** [P0]: Install & Configure SurrealDB 2.0+.
- [x] **M01.SETUP.003** [P0]: Install Redis 7+.
- [x] **M01.SETUP.004** [P0]: Initialize Project Structure & Git.

### Database Schema (SurrealDB)
- [x] **M01.DEV.001** [P0]: Define Namespaces & Databases (`infrastructure/surrealdb/schema.surql`).
- [x] **M01.DEV.002** [P0]: Create `memory` table (Vectors, HNSW Index).
- [x] **M01.DEV.003** [P0]: Create `entity` table & `relationship` (Graph Edges).
- [ ] **M01.DEV.004** [P0]: Define Custom Functions (Decay, Promotion). *(Implemented in `schema.py` but not connected to Client)*
- [ ] **M01.DEV.005** [P0]: Implement RBAC & Multi-Tenancy. *(Implemented in `schema.py` but not connected to Client)*

### Core Logic
- [x] **M01.DEV.006** [P0]: Implement SurrealDB Client Wrapper (Async, WebSocket).
- [x] **M01.DEV.007** [P1]: Implement Basic CRUD Operations.

---

## Module 02: Search System (Retrieval)

- [x] **M02.DEV.001** [P0]: Implement Vector Search (HNSW).
- [x] **M02.DEV.002** [P0]: Implement BM25 Full-Text Search.
- [x] **M02.DEV.003** [P0]: Implement Metadata Filtering.
- [x] **M02.DEV.004** [P0]: Create **Hybrid Search Orchestrator** (Vector + BM25 + Filter).
- [x] **M02.DEV.005** [P0]: Implement **Query Intent Classifier** (Routing).
- [x] **M02.DEV.006** [P1]: Implement Caching Layer (L1/L2/L3).
- [x] **M02.DEV.007** [P1]: Implement **Context Assembler** (Token Management).

---

## Module 03: Memory Lifecycle (Management)

- [x] **M03.DEV.001** [P0]: Implement **3-Tier Hierarchy Manager** (Working, Short, Long).
- [x] **M03.DEV.002** [P0]: Implement **Auto-Promotion Logic**.
- [ ] **M03.DEV.003** [P0]: Implement **Consolidation System** (Merging). *(Agent logic exists; Automation missing)*
- [x] **M03.DEV.004** [P0]: Implement **Decay Scoring Algorithm**.
- [ ] **M03.DEV.005** [P0]: Implement **Deduplication** (Hash-based + Semantic). *(Semantic exists via Agents; Hash-based missing)*
- [x] **M03.DEV.006** [P1]: Implement Archival System.

---

## Module 04: Processing & Analysis (Intelligence)

- [x] **M04.DEV.001** [P0]: Implement **Entity Extractor** (NER via LLM).
- [x] **M04.DEV.002** [P0]: Implement **Relationship Extractor** (Graph Building).
- [x] **M04.DEV.003** [P0]: Implement **Temporal Analyzer** (Recency weighting).
- [x] **M04.DEV.004** [P0]: Implement **Background Job Scheduler** (Daily/Weekly tasks).
- [x] **M04.DEV.005** [P1]: Implement **Skill Library** (Pattern -> Skill).
- [x] **M04.DEV.006** [P1]: Implement **Instruction Registry**.

---

## Module 05: Integration & Coordination

- [x] **M05.DEV.001** [P0]: Implement **MCP Server** (Model Context Protocol).
- [x] **M05.DEV.002** [P0]: Implement MCP Tools (`store`, `retrieve`, `consolidate`).
- [x] **M05.DEV.003** [P0]: Implement **Multi-Agent Orchestrator**.
- [x] **M05.DEV.004** [P0]: Implement **LIVE Subscriptions** (Real-time events).
- [x] **M05.DEV.005** [P1]: Implement Health Checks & Metrics Collection.

---

## Module 06: Cost Optimization

- [ ] **M06.DEV.001** [P0]: Implement **LLM Cascade Router** (Fast/Medium/Smart).
- [ ] **M06.DEV.002** [P0]: Implement **Task Complexity Classifier**.
- [ ] **M06.DEV.003** [P0]: Implement Cost Tracking System.
- [ ] **M06.DEV.004** [P1]: Implement **Consistency Signals** (Confidence Routing).
- [ ] **M06.DEV.005** [P2]: Implement **Mixture of Thought** (Parallel Extraction).

---

## Module 07: Quality Assurance

- [ ] **M07.DEV.001** [P0]: Implement **Self-Verification Loop** (6-check gate).
- [ ] **M07.DEV.002** [P0]: Implement **Multi-Agent Debate** (Analyzer/Synthesizer/Curator).
- [ ] **M07.DEV.003** [P1]: Implement **Information Traceability** (Provenance).

---

## Module 08: Advanced Search

- [ ] **M08.DEV.001** [P1]: Implement **Advanced Multi-Index Strategy** (7+ indexes).
- [ ] **M08.DEV.002** [P2]: Implement **Multi-Perspective Questions** (Expansion).
- [ ] **M08.DEV.003** [P2]: Implement **Topic Change Detection**.
- [ ] **M08.DEV.004** [P2]: Implement **Cross-Session Pattern Recognition**.

---

## Module 09: Production Features

- [ ] **M09.DEV.001** [P0]: Implement **Audit Logging System**.
- [ ] **M09.DEV.002** [P1]: Implement **Bi-temporal Graph Edges**.
- [ ] **M09.DEV.003** [P1]: Implement **Distributed Consolidation**.
- [ ] **M09.DEV.004** [P2]: Implement **Hyperedges** & Relationship Inheritance.
- [ ] **M09.DEV.005** [P2]: Create Standard Operating Procedures (SOPs).

---

## Module 10: Advanced Capabilities (Novelty)

- [ ] **M10.DEV.001** [P1]: Implement **Multimodal Support** (Image/Table/Code storage).
- [ ] **M10.DEV.002** [P1]: Implement **Cross-Modal Retrieval**.
- [ ] **M10.DEV.003** [P2]: Implement **AST Code Representation**.
- [ ] **M10.DEV.004** [P2]: Implement **Multi-Step Planning** & Hierarchical Decomposition.
- [ ] **M10.DEV.005** [P2]: Implement **Hypothesis Testing Framework**.
- [ ] **M10.DEV.006** [P1]: Integrate **Graph Visualization** Data Feed (for UI).

---

## Deployment & Documentation Tasks

- [ ] **DOC.001**: Complete all Architecture & Strategy Docs.
- [ ] **DEPLOY.001**: Security Audit & Performance Benchmarking.
- [ ] **DEPLOY.002**: Production Setup & Database Migration.
- [ ] **DEPLOY.003**: Monitoring & Alerting Setup.

---

**Total Estimated Tasks**: ~350
