# AGENTS.md: AI Developer Guide

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)
**Version**: 2.0
**Status**: Advanced Implementation Phase (Modules 1-10 Complete)

---

## 1. Documentation Map (Refactored Structure)

You **MUST** consult the following documents before starting work. They are the source of truth.

### 🔴 Critical Task Lists (Start Here)
- **[001-project-plan-and-tasks.md](docs/001-project-plan-and-tasks.md)**: The **Master Plan** and **Active Backlog**. Contains the Overview, Roadmap, Task List (Pending & Completed), and Contributing Guidelines.
- **[002-strategy-master.md](docs/002-strategy-master.md)**: The **Strategy Bible**. Contains detailed descriptions of all 159 strategies (Core, Advanced, Optimization, Experimental).

### 🔵 Architecture & Specifications
- **[003-tech-architecture.md](docs/003-tech-architecture.md)**: Technical specifications, System Overview, Database Schema, and API references.
- **[004-ops-manual.md](docs/004-ops-manual.md)**: Operations guide covering Deployment, Testing, Security, Monitoring, and Troubleshooting.

### ⚪ Archive
- **[docs/_archive/](docs/_archive/)**: Legacy reports and previous document versions. **Do NOT modify or delete files here.**

---

## 2. Rules for Documentation

1.  **No Deletion**: Never delete a documentation file. If a file is obsolete or needs >10% refactoring, **move the original to `docs/_archive/`** first, then create the new/updated file in `docs/`.
2.  **Naming Convention**: Use `NNN-type-name.md` (e.g., `005-specs-newfeature.md`) for new files.
3.  **Size Limits**: Keep files between 300 and 1500 lines. Split if too large; merge if too small.
4.  **Granularity**: Maintain high detail. Do not summarize away implementation specifics.

---

## 3. Where to Work Next

1.  **Check `docs/001-project-plan-and-tasks.md`**: Look for unchecked boxes `[ ]` in the "PENDING TASKS" section.
2.  **Focus Areas**:
    - **Module 11 (SurrealDB Optimization)**: Implement computed properties, nested documents, and graph optimizations.
    - **Module 12 (Novelty)**: Implement experimental patterns like "Flows vs Crews".
3.  **Reference**: Use `docs/002-strategy-master.md` to understand the *requirements* of the task you picked.

---

## 4. Coding Standards

### Repository Hygiene
- **NO Binary Files**: Never commit `__pycache__`, `*.pyc`, `.DS_Store`, or compiled binaries.
- **Dependencies**: If you add a library, update `requirements.txt`.
- **Testing**: Write Unit Tests or Verification Scripts to prove your code works.

### Architecture Style (DDD)
- `khala/domain/`: Entities and Interfaces.
- `khala/infrastructure/`: Database and API clients.
- `khala/application/`: Business logic and services.
- `khala/interface/`: REST API, CLI, MCP.

### Implementation Protocol
1.  **Read Docs**: `001` (Tasks) -> `002` (Strategy) -> `003` (Tech).
2.  **Plan**: Create a plan using `set_plan`.
3.  **Implement**: Write code.
4.  **Verify**: Run scripts.
5.  **Update Docs**: Mark the task as `[x]` in `001-project-plan-and-tasks.md`.

**Welcome to the team.**
