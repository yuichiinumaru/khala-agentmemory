# KHALA v2.0 - ROADMAP & GAP ANALYSIS

**Last Updated**: May 2025
**Status**: Production Ready (85%) - Phase 3.2 "Surgical Intervention"

---

## 🚨 TIER 1: CRITICAL INTEGRATIONS (Immediate Priority)
*These components exist in code but need to be wired into the main application flow.*

### 1. Self-Verification Gate
- **Status**: Logic implemented in `khala.application.verification.verification_gate`.
- **Gap**: Not called in `MemoryLifecycleService.ingest_memory`.
- **Action**: Add `VerificationGate.verify_memory()` call before storage. Reject or flag low-quality memories.

### 2. Distributed Consolidation
- **Status**: Logic implemented in `MemoryLifecycleService`.
- **Gap**: currently runs in-process using `asyncio.gather`. Blocks main API under load.
- **Action**: Refactor to use a job queue (Redis/SurrealDB based) and separate worker process.

### 3. Intent Classification
- **Status**: Implemented in `IntentClassifier`.
- **Gap**: `HybridSearchService` has `auto_detect_intent=False` by default and fallback logic is weak.
- **Action**: Enable by default and implement strict routing (e.g., Fact -> BM25 only).

### 4. LLM Cascading & Model Registry
- **Status**: `GeminiClient` supports cascading.
- **Gap**: Many services (e.g., `MultimodalService`) hardcode strings like "gemini-2.0-flash".
- **Action**: Refactor all services to use `ModelRegistry` constants.

---

## 🧬 MODULE 14: ADAPTATION & EVOLUTION (New Harvest)
*Strategies harvested from "Awesome Adaptation of Agentic AI".*

### 1. Self-Challenging Memory Retrieval (Strategy 173)
- **Concept**: Verify retrieved memories against query intent before returning.
- **Action**: Implement `SelfChallengingService`.

### 2. Feedback-Driven Search Tuning (Strategy 174)
- **Concept**: Dynamically tune `alpha` and `top_k` based on agent feedback.
- **Action**: Implement `AdaptiveSearchTuner`.

### 3. Adaptive Query Routing (Strategy 172)
- **Concept**: Route queries to appropriate engines (Vector vs Graph vs Web) based on complexity.
- **Action**: Implement `QueryRouter` (Agent-based).

### 4. Adaptive Graph Evolution (Strategy 171)
- **Concept**: Repair graph structure based on retrieval failures.
- **Action**: Extend `IndexRepairService` with `GraphArchitect` logic.

---

## ✅ TIER 2: VALIDATED FEATURES (Implemented)
*These features were flagged as missing in external audits but ARE implemented.*

### 1. Multimodal Support
- **Implementation**: `khala.application.services.multimodal_service`
- **Capabilities**: Image ingestion, Gemini Vision analysis, Cross-modal search.

### 2. MCP Server (Model Context Protocol)
- **Implementation**: `khala.interface.mcp.server`
- **Capabilities**: Full FastMCP server with tools for search, storage, and verification.

### 3. Human-in-the-Loop
- **Implementation**: `khala.application.services.approval_service`
- **Capabilities**: Approval request persistence and status management.

### 4. Skill Library
- **Implementation**: `khala.infrastructure.persistence.skill_repository`
- **Capabilities**: Vector search for skills.

---

## 🚫 EXCLUDED / DEPRECATED
*These features are explicitly removed from the roadmap.*

- **GPU Acceleration**: We rely exclusively on `gemini-embedding-001` API. No local CUDA/ONNX support is planned.

---

## 📋 MODEL STANDARDS

| Type | Model ID | Notes |
| :--- | :--- | :--- |
| **Main LLM** | `gemini-2.5-pro` | Use for complex reasoning. |
| **Fast LLM** | `gemini-2.5-flash` | Use for routine tasks. |
| **Embedding** | `models/gemini-embedding-001` | Standard 768d text embeddings. |
