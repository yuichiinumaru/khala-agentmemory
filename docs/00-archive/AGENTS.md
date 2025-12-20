# KHALA AGENT MEMORY SYSTEM

## 📜 CONSTITUTION & GOVERNANCE
> "The code is the law, but the documentation is the constitution."

This document (`AGENTS.md`) is the single source of truth for the project.
Deviations from these rules are considered critical defects.

**VITAL ASSET PRESERVATION**:
$\forall File \in \{AGENTS.md, README.md, docs/*, .env*\}$:
**Edit(File) $\implies$ Ask(User)**.
Destructive edits to `AGENTS.md` are **FORBIDDEN**. Always integrate, never delete without consent.

---

## 1. 🏗️ CANONICAL STRUCTURE

### Source Code (`khala/`)
- `domain/`: Pure business logic and entities. No external dependencies.
- `application/`: Service orchestration and use cases.
- `infrastructure/`: External adapters (Gemini, SurrealDB, CLI).
- `interface/`: Entry points (REST API, CLI, MCP).

### Documentation (`docs/`)
- `01-plans.md`: Active implementation plans.
- `02-tasks.md`: The Execution Queue (Tier 1 Priorities).
- `03-architecture.md`: System design and constraints.
- `16-arc-harvest.md`: Analysis of ARC Prize strategies.

---

## 2. 🏗️ SYSTEM STATUS (v2.0 - Production Ready)
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

## 3. 🤖 MODEL STANDARDS
All agents and services MUST adhere to these model configurations:

| Role | Model ID | Use Case |
| :--- | :--- | :--- |
| **Reasoning / Logic** | `gemini-3-pro-preview` | Complex analysis, debate, consolidation. |
| **Fast / Routine** | `gemini-3-flash-preview` | Classification, simple summaries. |
| **Embeddings** | `models/gemini-embedding-001` | 768d text embeddings. |
| **Multimodal** | `models/multimodal-embedding-001` | Image/Vision embeddings. |

**RESTRICTIONS**:
- **NO GPU ACCELERATION**: Do not implement CUDA/ONNX local embeddings. Use Gemini API only.
- **NO HARDCODED MODELS**: Use `ModelRegistry` for model selection whenever possible.
- **NO DEPRECATED LIBS**: Never, under ABSOLUTE ANY circunstance, use the **deprecated** lib `google-generativeai` - instead, use ALWAYS `google-genai`.

---

## 4. 🛠️ ENGINEERING KERNEL (VIVI OS v2.2 Integration)

### A. ARCHITECTURE (Two-Layer Graph)
**Directives:**
1.  **Separation:** Frontend $\cap$ Backend = $\emptyset$.
2.  **Flow:** $User \to L_1 \to L_2 \to L_{Worker} \to L_2 \to L_1 \to User$.
3.  **Constraint:** Direct SQL in Controllers = $\bot$ (Forbidden).

### B. OPERATIONAL MODES
The Agent MUST switch states based on `Task_Type`.

*   **Mode A: PROACTIVE (Default)**
    *   **Trigger:** Feature | Refactor | Docs
    *   **Algorithm:** Read Docs -> Plan -> Test (Red) -> Code (Green) -> Verify.
    *   **Constraint:** No chatter ("I will do..."). Just Code.

*   **Mode B: PARANOID DETECTIVE (Debug)**
    *   **Trigger:** Error | Bug | Crash
    *   **Protocol:** Deconstruct -> Doubt -> Suspects -> Stakeout -> Verdict.
    *   **Constraint:** No Guesswork.

### C. CODING STANDARDS (The Stack)
- **Stack:** Python (Agno), TypeScript (Mastra).
- **Async First**: All I/O must be asynchronous (`async def`).
- **Type Hints**: Strict typing required.
- **Dependency Integrity**: Use lockfiles.
- **Security**: No secrets in code. Use `SurrealConfig` and env vars.

### D. WORKFLOW ALGORITHM (RPG Ritual)
1.  **Init (Discovery):** `ls -R`, Read Docs, Assert Knowledge.
2.  **Proposal (Structure):** If Impact > 1 File $\implies$ Update `docs/02-tasks.md`.
3.  **CodeGen (TDD):** While Test Fails -> Analyze -> Fix Minimal -> Stop Loss (3 retries).
4.  **Scale (Doc Sync):** Update Changelog, Update Tasks.

---

## 🚀 ROADMAP (Immediate Priorities)

1.  **Hook up Verification Gate**: Integrate `VerificationGate` into `ingest_memory`.
2.  **Enable Intent Classification**: Set `auto_detect_intent=True` in `HybridSearchService`.
3.  **Refactor Consolidation**: Move consolidation to a background worker pattern.
4.  **Enforce Model Registry**: Remove hardcoded model strings in services.
5.  **Active Reasoning**: Integrate `RefinementReasoningService` for complex queries.

---

## 🚫 FORBIDDEN ACTIONS
- Do NOT delete `AGENTS.md` (Integrate edits only).
- Do NOT add binary files to git.
- Do NOT use synchronous database calls.
- Do NOT implement local GPU embedding models.
