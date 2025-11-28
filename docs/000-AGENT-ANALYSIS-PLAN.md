# Agent Analysis and Implementation Plan

## 1. Analysis of Current Codebase

### Documentation
The `docs/` folder is well-structured and comprehensive, outlining the vision for KHALA v2.0.
*   **01-plan-overview.md**: Clear vision of combining Vector, Graph, and Temporal memory in SurrealDB.
*   **02-tasks-implementation.md**: Tracks progress. Module 01 (Foundation) is partially complete. Module 02 (Search) is the next priority.
*   **04-database-schema.md**: Defines the target schema (`memory`, `entity`, `relation`), which is critical for the graph capabilities.

### Codebase Structure
*   **Domain-Driven Design (DDD)**: The project follows DDD principles (`domain`, `infrastructure`, `application`, `interface`).
*   **SurrealDB Client**: `khala/infrastructure/surrealdb/client.py` exists and has basic connection pooling and CRUD for memories.
    *   *Gap*: The `initialize()` method only defines the `memory` table and `bm25` index. It is missing the `entity` and `relationship` table definitions specified in the docs.
    *   *Gap*: The client uses `AsyncSurreal` in type hints but imports `Surreal`. This suggests a potential issue or reliance on a specific version of the `surrealdb` library where `Surreal` handles async.
*   **Repositories**: `SurrealDBMemoryRepository` is implemented but simple. It lacks the advanced filtering logic required for the "Hybrid Search".
*   **Missing Components**:
    *   **Embedding Service**: No implementation found for generating embeddings (OpenAI/Local).
    *   **Hybrid Search Service**: No logic to combine Vector + BM25 scores + Reranking.
    *   **Graph Logic**: Entity extraction and graph traversal services are stubs or missing.

## 2. Evaluation of Current State

The foundation is laid but incomplete. The system can store and retrieve memories by ID, but it lacks the "intelligence" components:
1.  **Semantic Search**: Impossible without an Embedding Service.
2.  **Hybrid Search**: Not implemented.
3.  **Graph Memory**: Schema not initialized, logic missing.

**Readiness**: Low. The system is not yet ready for end-to-end usage as an intelligent memory store.

## 3. List of Tasks (Small-Medium Set)

Based on the analysis, the following tasks are prioritized to move from "Basic Storage" to "Intelligent Search".

### Task 1: Foundation Hardening (Module 01)
*   **Schema Update**: Update `SurrealDBClient.initialize()` to define `entity` and `relationship` tables.
*   **Dependency Fix**: Verify and fix the `surrealdb` client import/usage (Async vs Sync).

### Task 2: Embedding Infrastructure (Module 02)
*   **Interface**: Define `EmbeddingService` port in `domain`.
*   **Implementation**: Create `OpenAIEmbedding` and `LocalEmbedding` adapters in `infrastructure`.

### Task 3: Hybrid Search Engine (Module 02)
*   **Service**: Implement `HybridSearchService` in `application`.
*   **Logic**:
    1.  Fetch candidates via Vector Search (Semantic).
    2.  Fetch candidates via BM25 (Keyword).
    3.  Combine results using Reciprocal Rank Fusion (RRF).

### Task 4: Integration Test
*   Create a test suite that initializes the DB, creates a memory with an embedding, and retrieves it via Hybrid Search.

## 4. Trace Plan to Begin Implementations

This plan outlines the steps to execute the tasks above.

1.  **Step 1: Fix Database Initialization**
    *   Modify `khala/infrastructure/surrealdb/client.py`.
    *   Add `DEFINE TABLE entity ...` and `DEFINE TABLE relationship ...` queries to `initialize()`.

2.  **Step 2: Create Embedding Service**
    *   Create `khala/domain/ports/embedding_service.py` (Abstract Base Class).
    *   Create `khala/infrastructure/embeddings/openai_embedding.py` (Uses `openai` lib).

3.  **Step 3: Implement Hybrid Search**
    *   Create `khala/application/services/hybrid_search_service.py`.
    *   Inject `MemoryRepository` and `EmbeddingService`.
    *   Implement `search(query, user_id)` method that orchestrates the two searches and merges them.

4.  **Step 4: Verify**
    *   Write a `pytest` integration test (`tests/integration/test_hybrid_flow.py`).
    *   Mock the OpenAI API calls to avoid costs/keys during basic testing.
    *   Verify that `search` returns the expected memory ID.
