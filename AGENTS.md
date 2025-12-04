# AGENTS.md: AI Developer Guide

**Project**: KHALA (Knowledge Hierarchical Adaptive Long-term Agent)
**Version**: 2.0.1 (Forge v2 Compliant)
**Status**: Advanced Implementation Phase (Audit: Critical Issues Resolved in Module 11)

---

## 1. Prime Directives (The Law)

1.  **Documentation is King**: The code is NOT the source of truth. The documentation is. If code contradicts documentation, the code is wrong.
2.  **No Ghost Features**: You are forbidden from implementing features not explicitly listed in `docs/02-tasks-implementation.md`.
3.  **No Binary Files**: Never commit `__pycache__`, `*.pyc`, `.DS_Store`, or compiled binaries.
4.  **Stop-Loss Protocol**: If you fail to fix an error after **3 attempts**, STOP. Document the failure and ask for help.

---

## 2. Project Context

KHALA is an advanced memory system for AI agents, built on **SurrealDB** and **Agno**.

-   **Current State**: Modules 01-10 are complete. Module 11 (Spatial) is fixed. Module 15 (Version Control) is missing.
-   **Architecture**: Domain-Driven Design (DDD).
    -   `khala/domain/`: Pure entities/logic.
    -   `khala/application/`: Services/orchestration.
    -   `khala/infrastructure/`: DB/API clients.
    -   `khala/interface/`: API/CLI/Tools.

---

## 3. Documentation Map

You **MUST** consult these before working:

### 🔴 Critical (Read First)
-   **[docs/02-tasks-implementation.md](docs/02-tasks-implementation.md)**: The **active backlog**. Check here for what to do. Update it when done.
-   **[docs/06-strategies-master.md](docs/06-strategies-master.md)**: The Strategy Bible. Definitions of all 170 strategies.

### 🔵 Technical
-   **[docs/04-database-schema.md](docs/04-database-schema.md)**: SurrealDB schema reference. (Code: `khala/infrastructure/surrealdb/schema.py`).
-   **[docs/11-surrealdb-optimization.md](docs/11-surrealdb-optimization.md)**: Optimization specs.
-   **[docs/12-novel-experimental.md](docs/12-novel-experimental.md)**: Experimental features.

### ⚪ Archive
-   `docs/_archive/`: Old files. Do not use for current status.

---

## 4. Development Workflow

1.  **Plan**: Read the task in `docs/02-tasks-implementation.md`. Create a plan using `set_plan`.
2.  **Verify Environment**: Ensure `surrealdb` is accessible (use `scripts/check_conn.py` if needed).
3.  **Implement**: Write code in `khala/`. Follow DDD.
4.  **Verify**:
    -   Write a temporary verification script in `scripts/verify_mytask.py`.
    -   Run it.
    -   Delete it before submitting.
    -   OR run existing tests: `python scripts/run_all_tests.py`.
5.  **Document**: Mark the task `[x]` in `docs/02-tasks-implementation.md`.
6.  **Submit**: Follow pre-commit instructions.

## 5. Scripts & Tools

-   **`scripts/`**: Utility scripts for checking connections, strategies, and running tests.
-   **`tests/`**: Unit and integration tests.
-   **`setup.py`**: Project installation (`pip install -e .`).

---

**Welcome to the Forge.**
