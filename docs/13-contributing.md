# 13-CONTRIBUTING.md: Contributing Guidelines

**Project**: KHALA v2.0
**Reference**: [02-tasks-implementation.md](02-tasks-implementation.md)

---

## 1. Code Standards

*   **Language**: Python 3.11+.
*   **Style**: PEP 8 (enforced by `ruff`).
*   **Types**: Strict typing (`mypy`).
*   **Async**: All I/O must be async (`async def`).

## 2. Git Workflow

1.  **Branch**: `feature/M01-setup-db` (Module + Task ID).
2.  **Commit**: `feat: implement vector index (M01.DEV.005)`.
3.  **PR**: Link to task in `02-tasks-implementation.md`.

## 3. Definition of Done

*   [ ] Code implemented.
*   [ ] Unit tests passing (>80% coverage).
*   [ ] Docstrings added.
*   [ ] Task status updated in `02-tasks-implementation.md`.

## 4. Reporting Issues

Use GitHub Issues with the label `bug` or `enhancement`. Include logs and reproduction steps.
