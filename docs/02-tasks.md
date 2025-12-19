# KHALA MASTER TASK BACKLOG (02-tasks.md)

## 🔴 P0: CRITICAL (Fundamental Governance & Implementation)

### 1. [ ] Implement NER Integration in `KHALAMemoryProvider` <!-- id: 800 -->
**Source**: [NER Spec](file:///home/suportesaude/YUICHI/00-VIVI/packages/khala-agentmemory/docs/00-archive/tasks/02_entity_extraction_service.md)
- [ ] **Infrastructure Setup** <!-- id: 801 -->
    - [ ] Create `khala/application/services/entity_extraction.py`. <!-- id: 802 -->
    - [ ] Define `ExtractedEntity` and `EntityRelationship` dataclasses. <!-- id: 803 -->
- [ ] **Core Logic** <!-- id: 804 -->
    - [ ] Implement `GeminiNERService` using `google-genai` (Native). <!-- id: 805 -->
    - [ ] Configure prompts for 8 entity types: PERSON, ORG, TOOL, CONCEPT, PLACE, EVENT, DATE, NUMBER. <!-- id: 806 -->
    - [ ] Implement confidence scoring (0.0-1.0) and relationship detection. <!-- id: 807 -->
- [ ] **Integration** <!-- id: 808 -->
    - [ ] Update `KHALAMemoryProvider.process_memory_entities` to call the service. <!-- id: 809 -->
    - [ ] Map extracted entities/relationships to SurrealDB `entity` and `relationship` tables. <!-- id: 810 -->
- [ ] **Verification** <!-- id: 811 -->
    - [ ] Write unit tests for extraction accuracy (>85%). <!-- id: 812 -->
    - [ ] Integration test: Full ingestion flow from `KHALAAgent` message to SurrealDB graph. <!-- id: 813 -->

### 2. [ ] Reorganize README Strategy Checklist <!-- id: 814 -->
- [ ] Implement `<details>` tags for all 5 sections of strategies. <!-- id: 815 -->

### 3. [ ] Fix SurrealDB Concurrency in `FlowOrchestrator` <!-- id: 816 -->
- [ ] Replace direct client calls with `FlowRepository` calls. <!-- id: 817 -->

---

## 🟡 P1: HIGH (Resurrection & Knowledge Consolidation)

### 4. [ ] Standardize Repositories <!-- id: 818 -->
- [ ] Audit all services for direct DB client usage (Forbidden by `AGENTS.md`). <!-- id: 819 -->
- [ ] Refactor `AuditRepository` to include transaction safety. <!-- id: 820 -->

### 5. [ ] Console Dashboard Wiring <!-- id: 821 -->
- [ ] Connect `khala-console` to the `MonitoringService` API. <!-- id: 822 -->

---

## 🟢 P2: MEDIUM (Cognitive Optimization)

### 6. [ ] Enable Self-Verification Gate <!-- id: 823 -->
- [ ] Integrate `VerificationGate` into `MemoryLifecycleService.ingest_memory`. <!-- id: 824 -->

---

## ✅ COMPLETED
- [x] Initial Codebase Deep-Dive Audit. <!-- id: 825 -->
- [x] Establishment of Forge Methodology v2.2 constitution in `AGENTS.md`. <!-- id: 826 -->
- [x] Systematic Archival of legacy documentation to `docs/00-archive/`. <!-- id: 827 -->
- [x] Synthesis of Master Plan (Index) and domain-specific sub-plans. <!-- id: 828 -->
