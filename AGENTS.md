# AGENTS.md: AI Developer Guide

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)
**Version**: 2.0
**Status**: Advanced Implementation Phase (Modules 1-10 Complete)

---

## 1. Project Status & Context

The KHALA project is in an advanced stage of development.
- **Modules 01-10 (Foundation to Advanced Capabilities)** are largely **COMPLETE**. This includes the core SurrealDB infrastructure, memory lifecycle (with automated consolidation/deduplication), multimodal support, and search systems.
- **Current Focus**: We are now entering **Phase 2: Optimization & Novelty**. The primary active tasks are in **Module 11 (SurrealDB Optimizations)** and **Module 12 (Novel/Experimental Strategies)**.

**Goal**: To implement the remaining strategies from the [159-Strategy Master List](docs/06-strategies-master.md), creating the ultimate reference implementation for an AI memory system.

---

## 2. Documentation Map

You **MUST** consult the following documents before starting work. They are the source of truth.

### 🔴 Critical Task Lists (Start Here)
- **[02-tasks-implementation.md](docs/02-tasks-implementation.md)**: The **active backlog**. Top sections list PENDING tasks (Modules 11 & 12). Bottom sections list COMPLETED tasks. **Update this file as you complete work.**
- **[06-strategies-master.md](docs/06-strategies-master.md)**: The "Bible" of project strategies. If you need to understand *what* a feature is (e.g., "Vector Attention"), look here.

### 🔵 Architecture & Specifications
- **[03-architecture-technical.md](docs/03-architecture-technical.md)**: System design and data flow.
- **[04-database-schema.md](docs/04-database-schema.md)**: SurrealDB schema reference. Note: `khala/infrastructure/surrealdb/schema.py` is the code implementation and must stay synced.
- **[11-surrealdb-optimization.md](docs/11-surrealdb-optimization.md)**: Detailed specs for the active optimization tasks.
- **[12-novel-experimental.md](docs/12-novel-experimental.md)**: Detailed specs for experimental features.

### ⚪ Archive
- **[docs/_archive/](docs/_archive/)**: Old analysis reports, audit logs, and previous implementation plans. Do not rely on these for current task status; use `02-tasks-implementation.md` instead.

---

## 3. Where to Work Next

1.  **Check `docs/02-tasks-implementation.md`**: Look for unchecked boxes `[ ]` in the top section ("PENDING TASKS").
2.  **Focus Areas**:
    - **Module 11 (Optimization)**: Improving database performance and structure (e.g., computed fields, graph traversal optimizations).
    - **Module 12 (Novelty)**: Implementing experimental agent patterns (e.g., episodic memory, crew patterns).
3.  **Refactoring**: If you see code that doesn't align with the completed modules (e.g., missing audit logging in a new service), fix it.

---

## 4. Coding Standards & Rules

### Repository Hygiene
- **NO Binary Files**: Never commit `__pycache__`, `*.pyc`, `.DS_Store`, or compiled binaries.
- **Dependencies**: If you add a library, update `requirements.txt`.
- **Testing**: We lack a full integration test suite due to environment limits (no running DB). Write **Unit Tests** or **Verification Scripts** (`verify_xyz.py`) to prove your code runs/imports correctly, then delete them before submitting.

### Architecture Style
- **Domain-Driven Design (DDD)**:
    - `khala/domain/`: Entities and Interfaces (Pure Python, no DB code).
    - `khala/infrastructure/`: Database clients, API clients (SurrealDB, Gemini).
    - `khala/application/`: Business logic, services, orchestration.
    - `khala/interface/`: REST API, CLI, MCP tools.
- **Do NOT Mix Layers**: Do not put SQL queries in the Domain layer. Do not put HTTP handlers in the Application layer.

### Implementation Protocol
1.  **Read Docs**: Understand the strategy from `06-strategies-master.md`.
2.  **Plan**: Create a plan using `set_plan`.
3.  **Implement**: Write code.
4.  **Verify**: Run a script to ensure it imports and behaves as expected (mocking DB if needed).
5.  **Update Docs**: Mark the task as `[x]` in `02-tasks-implementation.md`.

---

## 5. Quick Start for Agents

1.  **Explore**: `ls -R khala/` to see the structure.
2.  **Read**: `cat docs/02-tasks-implementation.md` to see what's left.
3.  **Action**: Pick a task from Module 11, implement it, verify it, submit.

**Welcome to the team.**
