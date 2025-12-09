# KHALA AGENT MEMORY SYSTEM

## 📜 CONSTITUTION & GOVERNANCE
> "The code is the law, but the documentation is the constitution."

This document (`AGENTS.md`) is the single source of truth for the project.
Deviations from these rules are considered critical defects.

---

## 🏗️ SYSTEM STATUS (v2.0 - Production Ready)
**Overall Completion**: 87%
**Verification**: 22/22 Core Strategies Implemented

### ✅ IMPLEMENTED & VERIFIED
- **Storage**: Vector (HNSW), Graph, Document, 3-Tier Hierarchy.
- **Advanced Features**: Multimodal (Image/Text), MCP Server, Human-in-the-Loop (Approval Service), Skill Library.
- **Reasoning**: **Refinement Loop (SOAR)**, **Product of Experts (PoE)**.
- **Infrastructure**: SurrealDB v2.0, Agno, Gemini 2.5 Pro.

### ⚠️ CRITICAL GAPS (Needs Integration)
These components exist in the codebase but require wiring into the main pipeline:
1.  **Self-Verification Gate**: `VerificationGate` logic exists but is not called in `MemoryLifecycleService`.
2.  **Distributed Consolidation**: Consolidation logic is currently in-process (`asyncio.gather`). Needs Redis/Queue worker separation for scale.
3.  **Intent Classification**: `IntentClassifier` exists but is disabled by default in search.
4.  **LLM Cascading**: Logic exists in `GeminiClient` but some services use hardcoded model IDs.

---

## 🤖 MODEL STANDARDS
All agents and services MUST adhere to these model configurations:

| Role | Model ID | Use Case |
| :--- | :--- | :--- |
| **Reasoning / Logic** | `gemini-2.5-pro` | Complex analysis, debate, consolidation. |
| **Fast / Routine** | `gemini-2.5-flash` | Classification, simple summaries. |
| **Embeddings** | `models/gemini-embedding-001` | 768d text embeddings. |
| **Multimodal** | `models/multimodal-embedding-001` | Image/Vision embeddings. |

**RESTRICTIONS**:
- **NO GPU ACCELERATION**: Do not implement CUDA/ONNX local embeddings. Use Gemini API only.
- **NO HARDCODED MODELS**: Use `ModelRegistry` for model selection whenever possible.

---

## 🛠️ PRIME DIRECTIVES

### 1. FILE STRUCTURE
- `khala/` is the root package.
- `tests/` contains `unit`, `integration`, and `stress`.
- `docs/` contains all documentation.
- `scripts/` contains utility scripts.

### 2. CODING STANDARDS
- **Async First**: All I/O must be asynchronous (`async def`).
- **Type Hints**: Strict typing required.
- **Error Handling**: Fail loudly on critical errors (e.g., startup), handle gracefully in loops.
- **Security**: No secrets in code. Use `SurrealConfig` and env vars.

### 3. DOCUMENTATION
- Update `docs/` when changing architecture.
- Keep `AGENTS.md` updated with high-level status.

---

## 🚀 ROADMAP (Immediate Priorities)

1.  **Hook up Verification Gate**: Integrate `VerificationGate` into `ingest_memory`.
2.  **Enable Intent Classification**: Set `auto_detect_intent=True` in `HybridSearchService`.
3.  **Refactor Consolidation**: Move consolidation to a background worker pattern.
4.  **Enforce Model Registry**: Remove hardcoded model strings in services.
5.  **Active Reasoning**: Integrate `RefinementReasoningService` for complex queries.

---

## 🚫 FORBIDDEN ACTIONS
- Do NOT delete `AGENTS.md`.
- Do NOT add binary files to git.
- Do NOT use synchronous database calls.
- Do NOT implement local GPU embedding models.
