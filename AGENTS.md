# AGENTS.md: The Constitution of KHALA

**Protocol**: FORGE v2 (Strict Governance)
**Status**: ACTIVE
**Authority**: Absolute

---

## 1. The Prime Directives (The Law)

1.  **Hierarchy of Truth**: `docs/` > `src/`. If the code contradicts the documentation, the code is **WRONG**.
2.  **No Ghost Features**: You are forbidden from touching `src/` unless a specific task exists in `docs/02-tasks.md`.
3.  **Atomic Decomposition**: No task shall be vague. "Fix bugs" is illegal. "Fix SQL Injection in auth.py" is legal.
4.  **Stop-Loss Protocol**: If you fail to fix an error after **3 attempts**, STOP. Revert. Document. Ask for help.
5.  **Test-Driven Development (TDD)**: You must write the test *before* the fix.
6.  **Zero Trust**: All external inputs (CLI args, API payloads, Env vars) are malicious until proven otherwise.
7.  **Fail Fast**: Do not swallow critical exceptions. Crash the container rather than running in a zombie state.

---

## 2. The Canonical Structure

You must maintain this structure. Any deviation is Heresy.

### The Documentation Temple (`docs/`)
-   **`00-draft.md`**: Scratchpad. Transient thoughts.
-   **`01-plan.md`**: The Strategic Map. The "Why" and "What".
-   **`02-tasks.md`**: The Execution Queue. The "How". **Source of Action.**
-   **`03-architecture.md`**: The Blueprint. Module boundaries.
-   **`04-changelog.md`**: The History. Record of Life and Death.
-   **`05-ideas.md`**: The Parking Lot. Future dreams.
-   **`06-rules.md`**: The Coding Standards. Style, Patterns, Linters.

### The Source Code (`khala/`)
-   **`domain/`**: Pure business logic. No external deps.
-   **`application/`**: Orchestration.
-   **`infrastructure/`**: Dirty details (DB, LLM, CLI).
-   **`interface/`**: Entry points (REST, CLI).

### The Testing Ground (`tests/`)
-   **`unit/`**: Fast, isolated tests.
-   **`integration/`**: Slow, DB/LLM connected tests.
-   **`stress/`**: Chaos engineering.

---

## 3. Workflow (The Ritual)

1.  **Consult the Oracle**: Read `docs/02-tasks.md`. Pick the top priority task.
2.  **Plan**: Use `set_plan` to outline your move.
3.  **Execute**: Modify code.
4.  **Verify**: Run tests.
5.  **Record**: Update `docs/04-changelog.md`. Mark task complete in `docs/02-tasks.md`.
6.  **Submit**: Commit with semantic message.

---

**"Code without documentation is a zombie. Resurrect the soul first."**
