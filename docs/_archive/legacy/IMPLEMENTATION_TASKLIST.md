# IMPLEMENTATION_TASKLIST.md
# KHALA Core Implementation Tasklist (Backend)

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)
**Version**: 2.0
**Status**: Active Construction
**Focus**: Completing missing backend features (Non-GPU, Non-UI)

---

## 1. Agno Native Integration (PRIORITY #1)
*Objective: Make KHALA a true plug-and-play Memory backend for Agno, replacing the "Wrapper" pattern.*

- [ ] **1.1. Create `KhalaMemory` Class**
    - **Task**: Implement `agno.memory.Memory` interface (or `Storage` depending on latest Agno version).
    - **Location**: `khala/interface/agno/memory.py`
    - **Deliverable**: A class that can be passed to `Agent(memory=KhalaMemory())`.
    - **Test**: `test_agno_native_integration.py` passing with standard Agno agent.

- [ ] **1.2. Implement `KhalaKnowledgeBase` Class**
    - **Task**: Implement `agno.knowledge.KnowledgeBase` for RAG capabilities using KHALA's search.
    - **Location**: `khala/interface/agno/knowledge.py`
    - **Deliverable**: A class connecting Agno's RAG loop to KHALA's Hybrid Search.
    - **Test**: Verify `agent.print_response("query", knowledge_base=khala_kb)` works.

- [ ] **1.3. Refactor `KHALAAgent`**
    - **Task**: Deprecate the wrapper. Update it to be a factory function that returns a standard `agno.Agent` configured with `KhalaMemory`.
    - **Deliverable**: Simplified `create_khala_agent` function.
    - **Test**: Ensure existing tests pass with the new factory pattern.

## 2. Memory Lifecycle & Consolidation (Missing Module)
*Objective: Implement the "Self-Organizing" brain features (Decay, Promotion, Merging).*

- [ ] **2.1. Implement Decay Logic**
    - **Task**: Create `DecayService` in `khala/domain/consolidation/`.
    - **Logic**: Calculate new scores based on `fn::decay_score` strategy.
    - **Deliverable**: Service that updates `decay_score` on memory records.
    - **Test**: Verify older memories have lower scores.

- [ ] **2.2. Implement Consolidation Manager**
    - **Task**: Create `ConsolidationService`.
    - **Logic**: Identify overlapping memories (Semantic > 0.95), merge content using LLM, archive originals.
    - **Deliverable**: `consolidate_memories(user_id)` function.
    - **Test**: Create 2 nearly identical memories, run service, verify 1 merged memory remains.

- [ ] **2.3. Implement Auto-Promotion Background Job**
    - **Task**: Create a background job (using `apscheduler` or simple loop) to run `should_promote`.
    - **Logic**: Move `Working` -> `ShortTerm` -> `LongTerm` based on access/importance.
    - **Deliverable**: Running background task.
    - **Test**: Simulate access counts and verify tier change.

## 3. Advanced Search & Graph Traversal
*Objective: Activate the "Advanced" search features currently mocked.*

- [ ] **3.1. Wire up Advanced Query Expansion**
    - **Task**: Connect `khala/domain/search/query_expansion.py` (Gemini-based) to `HybridSearchService`.
    - **Deliverable**: Search pipeline using LLM-generated variations.
    - **Test**: Verify search logs show multiple query variations being executed.

- [ ] **3.2. Implement Graph Traversal Search**
    - **Task**: Implement `_graph_traversal_search` in `HybridSearchService`.
    - **Logic**: Use SurrealDB graph queries (`SELECT ->relationship->entity`) to find related memories.
    - **Deliverable**: Working graph search stage.
    - **Test**: Search for an entity, ensure related (2-hop) memories are returned.

- [ ] **3.3. Implement Cross-Session Patterns (Strategy #34)**
    - **Task**: Implement `SessionAnalyzer` to find recurring queries/topics across `search_session` table.
    - **Deliverable**: `get_user_patterns(user_id)` function.
    - **Test**: Simulate 5 sessions with same topic, verify pattern detected.

## 4. Entity Extraction & Knowledge Graph
*Objective: Replace placeholders with real Intelligence.*

- [ ] **4.1. Activate Entity Extraction**
    - **Task**: Implement `extract_entities` in `EntityService` using Gemini.
    - **Logic**: Parse text, identify (Person, Location, Concept), return `Entity` objects.
    - **Deliverable**: Real NER (Named Entity Recognition).
    - **Test**: Input text "John went to Paris", verify Entities "John" (Person) and "Paris" (Location).

- [ ] **4.2. Implement Relationship Detection**
    - **Task**: Logic to determine relationships between extracted entities.
    - **Deliverable**: `detect_relationships(text, entities)` returning `Relationship` objects.
    - **Test**: Verify "John lives in Paris" creates `(John)-[LIVES_IN]->(Paris)`.

- [ ] **4.3. Entity Deduplication**
    - **Task**: Logic to merge "John Smith" and "J. Smith" if context matches.
    - **Deliverable**: `deduplicate_entities()` job.
    - **Test**: Verify duplicate entities are merged in DB.

## 5. Missing Advanced Capabilities (Modules 09 & 10)
*Objective: Implement the high-value "Smart" features.*

- [ ] **5.1. Audit Logging System (Strategy #39)**
    - **Task**: Create `AuditService` and decorators for critical methods.
    - **Deliverable**: Every write/delete operation logs to `audit_log` table.
    - **Test**: Perform action, query `audit_log`, verify record.

- [ ] **5.2. Skill Library (Strategy #35)**
    - **Task**: Implement `khala/domain/skills/` logic to save successful code/plans as "Skills".
    - **Deliverable**: `SkillRepository` and `save_skill` workflow.
    - **Test**: Save a "skill", retrieve it via vector search.

- [ ] **5.3. Instruction Registry (Strategy #36)**
    - **Task**: Create a registry for system prompts and SOPs.
    - **Deliverable**: Database table `instruction` and access service.
    - **Test**: Retrieve instruction by name/version.

## 6. Testing & Quality Assurance
*Objective: Ensure the system is robust.*

- [ ] **6.1. Comprehensive Unit Test Suite**
    - **Task**: Fix all broken tests found in analysis.
    - **Deliverable**: `pytest` runs clean.

- [ ] **6.2. Load Testing Script**
    - **Task**: Script to insert 10k memories and measure search latency.
    - **Deliverable**: `scripts/load_test.py`.
    - **Test**: Verify p95 latency < 100ms.

- [ ] **6.3. Accuracy Benchmark**
    - **Task**: Script to verify recall/precision of Hybrid Search vs Vector only.
    - **Deliverable**: `scripts/benchmark_accuracy.py`.
